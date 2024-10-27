from odoo import models, fields

class StockInventoryDateReport(models.Model):
    _name = 'stock.inventory.date.report'
    _description = 'Reporte de Stock entre Fechas'

    location_id = fields.Many2one('stock.location', string="Ubicación", required=True)
    product_id = fields.Many2one('product.product', string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)

