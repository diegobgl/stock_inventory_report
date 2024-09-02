from odoo import models, fields, api

class StockInventoryReport(models.Model):
    _name = 'stock.inventory.report'
    _description = 'Reporte de Inventario a Fecha Pasada'

    location_id = fields.Many2one('stock.location', string='Ubicación')
    product_id = fields.Many2one('product.product', string='Producto')
    lot_id = fields.Many2one('stock.production.lot', string='Lote/Serie')
    last_move_date = fields.Datetime(string='Fecha Último Movimiento')
    move_type = fields.Selection([('Compra', 'Compra'), ('Transferencia Interna', 'Transferencia Interna')], string='Tipo de Movimiento')
    quantity = fields.Float(string='Cantidad')
    unit_value = fields.Float(string='Valor Unitario')
    total_value = fields.Float(string='Valorizado', compute='_compute_total_value')

    @api.depends('quantity', 'unit_value')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.quantity * line.unit_value


    @api.model
    def generate_report(self, date):
        self.env['stock.inventory.report'].search([]).unlink()  # Limpia reportes previos
        stock_moves = self.env['stock.move'].search([('date', '<=', date), ('state', '=', 'done')])
        inventory_data = {}
        for move in stock_moves:
            key = (move.product_id.id, move.location_id.id)
            if key not in inventory_data:
                inventory_data[key] = 0
            inventory_data[key] += move.product_qty if move.location_dest_id.id == move.location_id.id else -move.product_qty
        
        report_lines = []
        for (product_id, location_id), quantity in inventory_data.items():
            report_lines.append({
                'product_id': product_id,
                'location_id': location_id,
                'quantity': quantity,
                'date': date,
            })
        self.create(report_lines)

    def get_inventory_summary(self):
        # Aquí agregar la lógica para obtener el resumen del inventario
        total_products = len(self.search([]))
        total_quantity = sum(self.search([]).mapped('quantity'))
        total_value = sum(self.search([]).mapped(lambda r: r.quantity * r.product_id.standard_price))
        overdue_products = len(self.search([('date', '<', fields.Date.today())]))

        return {
            'total_products': total_products,
            'total_quantity': total_quantity,
            'total_value': total_value,
            'overdue_products': overdue_products,
        }