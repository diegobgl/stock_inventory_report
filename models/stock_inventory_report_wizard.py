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

            # Crear el registro del reporte con los datos obtenidos
            stock_inventory_report.create({
                'location_id': location.id,
                'product_id': product.id,
                'quantity': quantity,
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

        # Dominio básico para obtener los quants actuales
        domain_quant = [('location_id.usage', 'in', ['internal', 'transit'])]

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_quant.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_quant.append(('location_id', '=', self.location_id.id))

        # 1. Obtener el stock actual (a fecha actual)
        current_quants = self.env['stock.quant'].search(domain_quant)

        # 2. Obtener movimientos que ocurren después de la fecha seleccionada (date_to)
        moves_after_date = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>', date_to),  # Movimientos después de la fecha de consulta
            '|',
            ('location_id.usage', 'in', ['internal', 'transit']),
            ('location_dest_id.usage', 'in', ['internal', 'transit']),
        ] + domain_quant)

        # Inicializar diccionario de cantidades
        product_qty = {}

        # 3. Ajustar el stock actual en base a los movimientos que ocurrieron después de la fecha seleccionada
        for quant in current_quants:
            product_id = quant.product_id.id
            location_id = quant.location_id.id

            if (location_id, product_id) not in product_qty:
                product_qty[(location_id, product_id)] = quant.quantity

        # 4. Revertir los movimientos posteriores para obtener el stock en la fecha exacta
        for move in moves_after_date:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Si el movimiento es una salida después de la fecha de consulta, sumamos la cantidad de vuelta
            if move.location_id.usage in ['internal', 'transit']:
                if (location_id, product_id) not in product_qty:
                    product_qty[(location_id, product_id)] = 0
                product_qty[(location_id, product_id)] += move.product_uom_qty

            # Si el movimiento es una entrada después de la fecha de consulta, restamos la cantidad
            if move.location_dest_id.usage in ['internal', 'transit']:
                if (destination_location_id, product_id) not in product_qty:
                    product_qty[(destination_location_id, product_id)] = 0
                product_qty[(destination_location_id, product_id)] -= move.product_uom_qty

        # 5. Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in product_qty.items():
            if qty > 0:  # Solo mostrar productos con stock positivo
                result.append({
                    'location_id': self.env['stock.location'].browse(location_id),
                    'product_id': self.env['product.product'].browse(product_id),
                    'quantity': qty,
                })

        return result
