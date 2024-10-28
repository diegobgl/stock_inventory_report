from odoo import models, fields

class StockInventoryDateReport(models.Model):
    _name = 'stock.inventory.date.report'
    _description = 'Reporte de Inventario a Fecha'

    location_id = fields.Many2one('stock.location', string="Ubicación", required=True)
    product_id = fields.Many2one('product.product', string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    unit_value = fields.Float(string="Valor Unitario", required=True)  # Precio promedio ponderado
    total_value = fields.Float(string="Valor Total", compute='_compute_total_value', store=True)
    lot_name = fields.Char(string="Lote/Número de Serie")  # Lote o número de serie
    last_move_date = fields.Datetime(string="Fecha Último Movimiento")  # Fecha del último movimiento
    move_type = fields.Char(string="Tipo Movimiento")  # Tipo de movimiento: Compra o Transferencia Interna

 #   @api.depends('quantity', 'unit_value')
    def _compute_total_value(self):
        for record in self:
            record.total_value = record.quantity * record.unit_value
