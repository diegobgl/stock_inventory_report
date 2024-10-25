from odoo import models, fields, api

class StockInventoryReport(models.TransientModel):
    _name = 'stock.inventory.report'
    _description = 'Reporte de Inventario'

    product_id = fields.Many2one('product.product', string="Producto")
    location_id = fields.Many2one('stock.location', string="Ubicación")
    quantity = fields.Float(string="Cantidad")
    date = fields.Datetime(string="Fecha del Movimiento")
    move_type = fields.Char(string="Tipo de Movimiento")  # Campo para el tipo de movimiento
    unit_value = fields.Float(string="Valor Unitario")    # Campo para el valor unitario
    total_value = fields.Float(string="Valor Total")      # Campo para el valor total

