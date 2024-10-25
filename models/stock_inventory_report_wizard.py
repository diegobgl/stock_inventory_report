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
            product = move.get('product_id')
            location = move.get('location_id')
            quantity = move.get('product_uom_qty')  # Cantidad total movida

            if product and location:
                product_record = self.env['product.product'].browse(product[0])
                location_record = self.env['stock.location'].browse(location[0])

                # Crear registro en el reporte
                stock_inventory_report.create({
                    'product_id': product_record.id,
                    'location_id': location_record.id,
                    'quantity': quantity,
                    'unit_value': product_record.standard_price,  # Usamos el precio estándar del producto
                    'total_value': quantity * product_record.standard_price,  # Valor total = cantidad * precio unitario
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
        
        # Aplicar los filtros de fechas, ubicación y producto
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Agrupar por producto y ubicación
        moves = self.env['stock.move'].read_group(
            domain,
            ['product_id', 'location_id', 'product_uom_qty:sum'],  # Cantidad total movida
            ['product_id', 'location_id']  # Agrupamos por producto y ubicación
        )

        return moves

