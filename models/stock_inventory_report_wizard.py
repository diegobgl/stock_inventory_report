from odoo import models, fields, api
from datetime import datetime

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario a una fecha con recalculo de ajustes negativos'

    date_to = fields.Date(string="Hasta la fecha", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=False)
    product_id = fields.Many2one('product.product', string="Producto", required=False)

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.date.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo

        quants = self._get_stock_at_date()  # Obtener stock a la fecha seleccionada

        for quant in quants:
            location = quant['location_id']
            product = quant['product_id']
            quantity = quant['quantity']
            unit_value = quant['unit_value']  # Precio promedio calculado
            lot_name = quant.get('lot_name', '')  # Lote o número de serie
            last_move_date = quant.get('last_move_date', '')  # Fecha del último movimiento
            move_type = quant.get('move_type', '')  # Tipo de movimiento

            # Crear el registro del reporte con los datos obtenidos
            stock_inventory_report.create({
                'location_id': location.id,
                'product_id': product.id,
                'quantity': quantity,
                'unit_value': unit_value,  # Precio unitario promedio
                'total_value': unit_value * quantity,  # Valor total
                'lot_name': lot_name,  # Lote/Serie
                'last_move_date': last_move_date,  # Fecha del último movimiento
                'move_type': move_type,  # Tipo de movimiento
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario a Fecha',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.date.report',
            'target': 'main',
        }

    def _get_stock_at_date(self):
        date_to = self.date_to

        # Dominio básico para obtener los movimientos confirmados hasta la fecha seleccionada
        domain_moves = [('state', '=', 'done'), ('date', '<=', date_to)]

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_moves.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_moves.append('|')
            domain_moves.append(('location_id', '=', self.location_id.id))
            domain_moves.append(('location_dest_id', '=', self.location_id.id))

        # 1. Obtener los movimientos hasta la fecha seleccionada (entradas y salidas)
        moves = self.env['stock.move'].search(domain_moves)

        product_qty = {}
        product_value = {}  # Para calcular el valor total y el promedio ponderado
        product_lots = {}  # Para almacenar los lotes o números de serie
        product_last_move = {}  # Para almacenar la fecha del último movimiento
        product_move_type = {}  # Para almacenar el tipo del último movimiento

        # 2. Calcular el stock inicial a partir de los quants (cantidades reales en las ubicaciones)
        stock_initial = self._calculate_initial_stock()

        # Ajustar el stock inicial sumando entradas y restando salidas
        for move in moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Ajustar el stock basado en movimientos
            if (location_id, product_id) not in stock_initial:
                stock_initial[(location_id, product_id)] = 0

            if move.location_id.usage in ['internal', 'production', 'transit']:
                stock_initial[(location_id, product_id)] -= move.product_uom_qty

            if move.location_dest_id.usage in ['internal', 'production', 'transit']:
                if (destination_location_id, product_id) not in stock_initial:
                    stock_initial[(destination_location_id, product_id)] = 0
                stock_initial[(destination_location_id, product_id)] += move.product_uom_qty

                # Asignar el precio calculado o el precio estándar si no hay movimientos previos
                if (destination_location_id, product_id) not in product_value:
                    product_value[(destination_location_id, product_id)] = {
                        'total_value': 0, 'total_qty': 0}
                move_price_unit = move.price_unit or move.product_id.standard_price

                product_value[(destination_location_id, product_id)]['total_value'] += move.product_uom_qty * move_price_unit
                product_value[(destination_location_id, product_id)]['total_qty'] += move.product_uom_qty

                # Obtener el lote/número de serie desde las líneas del movimiento (move_line_ids)
                lot_name = ''
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        lot_name = move_line.lot_id.name
                        break  # Tomamos el primer lote encontrado para simplificar
                product_lots[(destination_location_id, product_id)] = lot_name

                # Almacenar la fecha del último movimiento
                product_last_move[(destination_location_id, product_id)] = move.date

                # Determinar el tipo de movimiento
                if move.picking_type_id.code == 'incoming':
                    move_type = 'Compra'
                else:
                    move_type = 'Transferencia Interna'
                product_move_type[(destination_location_id, product_id)] = move_type

        # 3. Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in stock_initial.items():
            if qty != 0:  # Mostrar tanto stock positivo como negativo
                total_value = product_value[(location_id, product_id)]['total_value'] if (location_id, product_id) in product_value else 0
                total_qty = product_value[(location_id, product_id)]['total_qty'] if (location_id, product_id) in product_value else qty
                unit_value = total_value / total_qty if total_qty > 0 else 0  # Precio promedio ponderado

                result.append({
                    'location_id': self.env['stock.location'].browse(location_id),
                    'product_id': self.env['product.product'].browse(product_id),
                    'quantity': qty,
                    'unit_value': unit_value,  # Precio promedio
                    'lot_name': product_lots.get((location_id, product_id), ''),
                    'last_move_date': product_last_move.get((location_id, product_id), ''),
                    'move_type': product_move_type.get((location_id, product_id), '')
                })

        return result

    def _calculate_initial_stock(self):
        """ Calcular el stock inicial usando los quants """
        stock_initial = {}

        # Buscar quants hasta la fecha actual para obtener el stock inicial
        quants = self.env['stock.quant'].search([
            ('location_id.usage', 'in', ['internal', 'transit']),  # Ubicaciones internas y en tránsito
            ('quantity', '!=', 0),  # Excluir quants vacíos
        ])

        # Calcular el stock inicial para cada producto en cada ubicación
        for quant in quants:
            location_id = quant.location_id.id
            product_id = quant.product_id.id
            if (location_id, product_id) not in stock_initial:
                stock_initial[(location_id, product_id)] = 0

            # Acumular la cantidad inicial del producto en esa ubicación
            stock_initial[(location_id, product_id)] += quant.quantity

        return stock_initial
