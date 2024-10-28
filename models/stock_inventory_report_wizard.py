from odoo import models, fields, api
from datetime import datetime

class StockInventoryDateReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para obtener inventario a una fecha '

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

            # Crear el registro del reporte con los datos obtenidos
            stock_inventory_report.create({
                'location_id': location.id,
                'product_id': product.id,
                'quantity': quantity,
                'unit_value': unit_value,  # Precio unitario promedio
                'total_value': unit_value * quantity  # Valor total
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

        # 1. Obtener los movimientos hasta la fecha seleccionada (entradas y salidas)
        moves = self.env['stock.move'].search(domain_moves)

        product_qty = {}
        product_value = {}  # Para calcular el valor total y el promedio ponderado

        for move in moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Si el movimiento es una salida, restamos la cantidad
            if move.location_id.usage in ['internal', 'transit']:
                if (location_id, product_id) not in product_qty:
                    product_qty[(location_id, product_id)] = 0
                product_qty[(location_id, product_id)] -= move.product_uom_qty

            # Si el movimiento es una entrada, sumamos la cantidad y registramos el valor
            if move.location_dest_id.usage in ['internal', 'transit']:
                if (destination_location_id, product_id) not in product_qty:
                    product_qty[(destination_location_id, product_id)] = 0
                product_qty[(destination_location_id, product_id)] += move.product_uom_qty

                # Calculamos el valor total de la entrada
                if (destination_location_id, product_id) not in product_value:
                    product_value[(destination_location_id, product_id)] = {
                        'total_value': 0, 'total_qty': 0}

                # **Ajuste clave aquí**: si es una ubicación de tránsito y el precio es 0, asignamos el precio promedio calculado de ubicaciones internas
                if move.location_dest_id.usage == 'transit' and not move.price_unit:
                    # Calculamos el precio promedio en ubicaciones internas
                    if (destination_location_id, product_id) in product_value and product_value[(destination_location_id, product_id)]['total_qty'] > 0:
                        avg_internal_price = product_value[(destination_location_id, product_id)]['total_value'] / product_value[(destination_location_id, product_id)]['total_qty']
                    else:
                        avg_internal_price = move.product_id.standard_price  # Asignamos el precio estándar como respaldo
                    move_price_unit = avg_internal_price
                else:
                    move_price_unit = move.price_unit

                # Actualizamos los valores en el diccionario
                product_value[(destination_location_id, product_id)]['total_value'] += move.product_uom_qty * move_price_unit
                product_value[(destination_location_id, product_id)]['total_qty'] += move.product_uom_qty

        # 2. Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in product_qty.items():
            if qty > 0:  # Solo mostrar productos con stock positivo
                total_value = product_value[(location_id, product_id)]['total_value']
                total_qty = product_value[(location_id, product_id)]['total_qty']
                unit_value = total_value / total_qty if total_qty > 0 else 0  # Precio promedio ponderado

                result.append({
                    'location_id': self.env['stock.location'].browse(location_id),
                    'product_id': self.env['product.product'].browse(product_id),
                    'quantity': qty,
                    'unit_value': unit_value  # Precio promedio
                })

        return result

