from odoo import models, fields

class StockInventoryDateReport(models.Model):
    _name = 'stock.inventory.date.report'
    _description = 'Reporte de Stock entre Fechas'

    location_id = fields.Many2one('stock.location', string="Ubicación", required=True)
    product_id = fields.Many2one('product.product', string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    unit_value = fields.Float(string="Valor Unitario", required=True)  # Precio promedio ponderado
    total_value = fields.Float(string="Valor Total", compute='_compute_total_value', store=True)

    #@api.depends('quantity', 'unit_value')
    def _compute_total_value(self):
        for record in self:
            record.total_value = record.quantity * record.unit_value

