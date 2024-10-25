from odoo import models, fields, api

class StockInventoryReport(models.Model):
    _name = 'stock.inventory.report'
    _description = 'Reporte de Inventario Histórico'

    product_id = fields.Many2one('product.product', string="Producto", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    unit_value = fields.Float(string="Valor Unitario", required=True)
    total_value = fields.Float(string="Valor Total", required=True)

