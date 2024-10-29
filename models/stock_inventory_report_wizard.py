from odoo import models, fields, api
from datetime import datetime

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario a una fecha con detalles'

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

        # Dominio básico para obtener los movimientos confirmados antes de la fecha
        domain_moves = [('state', '=', 'done'), ('date', '<=', date_to)]

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_moves.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_moves.append('|')
            domain_moves.append(('location_id', '=', self.location_id.id))
            domain_moves.append(('location_dest_id', '=', self.location_id.id))

        # Obtener los movimientos hasta la fecha seleccionada (entradas y salidas)
        moves = self.env['stock.move'].search(domain_moves)

        product_qty = {}
        product_value = {}  # Para calcular el valor total y el promedio ponderado
        product_lots = {}  # Para almacenar los lotes o números de serie
        product_last_move = {}  # Para almacenar la fecha del último movimiento
        product_move_type = {}  # Para almacenar el tipo del último movimiento

        for move in moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Si el movimiento es una salida a una ubicación virtual (descuento de stock)
            if move.location_dest_id.usage == 'virtual':
                if (location_id, product_id) not in product_qty:
                    product_qty[(location_id, product_id)] = 0
                product_qty[(location_id, product_id)] -= move.product_uom_qty

            # Si el movimiento es una entrada desde una ubicación virtual (aumento de stock)
            elif move.location_id.usage == 'virtual' and move.location_dest_id.usage in ['internal', 'transit']:
                if (destination_location_id, product_id) not in product_qty:
                    product_qty[(destination_location_id, product_id)] = 0
                product_qty[(destination_location_id, product_id)] += move.product_uom_qty

            # Si el movimiento es una entrada normal a ubicaciones internas, sumamos la cantidad
            if move.location_dest_id.usage in ['internal', 'transit']:
                if (destination_location_id, product_id) not in product_qty:
                    product_qty[(destination_location_id, product_id)] = 0
                product_qty[(destination_location_id, product_id)] += move.product_uom_qty

                # Calcular el valor del producto
                if (destination_location_id, product_id) not in product_value:
                    product_value[(destination_location_id, product_id)] = {
                        'total_value': 0, 'total_qty': 0}
                move_price_unit = move.price_unit or move.product_id.standard_price

                product_value[(destination_location_id, product_id)]['total_value'] += move.product_uom_qty * move_price_unit
                product_value[(destination_location_id, product_id)]['total_qty'] += move.product_uom_qty

                # Asignar el lote/número de serie si existe en las líneas del movimiento
                lot_name = ''
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        lot_name = move_line.lot_id.name
                        break  # Tomamos el primer lote encontrado
                product_lots[(destination_location_id, product_id)] = lot_name

                # Almacenar la fecha del último movimiento
                product_last_move[(destination_location_id, product_id)] = move.date

                # Determinar el tipo de movimiento
                move_type = 'Compra' if move.picking_type_id.code == 'incoming' else 'Transferencia Interna'
                product_move_type[(destination_location_id, product_id)] = move_type

        # Considerar movimientos negativos (ajustes iniciales o cargas negativas)
        stock_initial = self._calculate_initial_stock(domain_moves, product_qty)

        # Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in product_qty.items():
            if qty != 0:  # Mostrar tanto stock positivo como negativo
                total_value = product_value.get((location_id, product_id), {}).get('total_value', 0)
                total_qty = product_value.get((location_id, product_id), {}).get('total_qty', 1)
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
        

    def _calculate_initial_stock(self, product_qty):
        domain_quants = []
        
        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_quants.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_quants.append(('location_id', '=', self.location_id.id))

        # Buscar los quants relevantes
        initial_stock = self.env['stock.quant'].search(domain_quants)
        
        # Ajustar el stock basado en los quants encontrados
        for quant in initial_stock:
            key = (quant.location_id.id, quant.product_id.id)
            if key not in product_qty:
                product_qty[key] = 0
            product_qty[key] += quant.quantity

        return product_qty
