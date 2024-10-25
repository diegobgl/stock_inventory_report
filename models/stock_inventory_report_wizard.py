from odoo import api, fields, models
import logging


class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario'

    date_from = fields.Date(string="Desde la fecha", required=True)
    date_to = fields.Date(string="Hasta la fecha", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=False)
    product_id = fields.Many2one('product.product', string="Producto", required=False)
    lot_id = fields.Many2one('stock.production.lot', string="Lote", required=False)


    _logger = logging.getLogger(__name__)

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo

        moves = self._get_stock_moves()  # Obtener los movimientos agrupados

        for move in moves:
            # Verificar si hay información del movimiento y procesar
            product = move.get('product_id')
            location = move.get('location_id')
            date = move.get('date')
            quantity = move.get('quantity_done')
            picking_type = move.get('picking_type_id')

            if product and location and date:
                product_record = self.env['product.product'].browse(product[0])
                location_record = self.env['stock.location'].browse(location[0])
                picking_type_record = self.env['stock.picking.type'].browse(picking_type[0])

                unit_value = product_record.standard_price
                total_value = quantity * unit_value  # Valor total del producto

                stock_inventory_report.create({
                    'product_id': product_record.id,
                    'location_id': location_record.id,
                    'quantity': quantity,
                    'date': date,
                    'move_type': 'Compra' if picking_type_record.code == 'incoming' else 'Traslado Interno',
                    'unit_value': unit_value,
                    'total_value': total_value,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario Histórico',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.report',
            'target': 'main',
        }




# Obtener el logger de Odoo para registrar los errores
    _logger = logging.getLogger(__name__)

    def _get_stock_moves(self):
        # Dominio para filtrar movimientos confirmados entre las fechas seleccionadas
        domain = [('state', '=', 'done')]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.lot_id:
            domain.append(('lot_id', '=', self.lot_id.id))

        # Agrupar por producto y ubicación para obtener el último movimiento
        moves = self.env['stock.move'].read_group(
            domain,
            ['product_id', 'location_id', 'date:max', 'quantity_done:sum', 'picking_type_id'],
            ['product_id', 'location_id']
        )

        return moves