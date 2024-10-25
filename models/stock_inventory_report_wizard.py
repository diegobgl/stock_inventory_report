from odoo import api, fields, models

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario'

    date_from = fields.Date(string="Desde la fecha", required=True)
    date_to = fields.Date(string="Hasta la fecha", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=False)
    product_id = fields.Many2one('product.product', string="Producto", required=False)
    lot_id = fields.Many2one('stock.production.lot', string="Lote", required=False)

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo
        
        moves = self._get_stock_moves()  # Obtener los movimientos basados en los filtros

        for move in moves:
            # Calcular el valor total basado en la cantidad y el valor unitario
            unit_value = move.product_id.standard_price
            total_value = move.product_uom_qty * unit_value
            
            stock_inventory_report.create({
                'product_id': move.product_id.id,
                'location_id': move.location_id.id,
                'quantity': move.product_uom_qty,
                'lot_id': move.lot_id.id if move.lot_id else False,
                'date': move.date,
                'move_type': move.picking_type_id.name or move.reference,  # Asignar tipo de movimiento
                'unit_value': unit_value,  # Valor unitario del producto
                'total_value': total_value,  # Valor total (cantidad * valor unitario)
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.report',
            'target': 'main',
        }

    def _get_stock_moves(self):
        # Filtramos los movimientos de stock con el ORM según los parámetros seleccionados
        domain = [('state', '=', 'done')]  # Solo movimientos confirmados
        
        # Aplicar filtros del wizard
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
        
        # Retornar los movimientos filtrados
        return self.env['stock.move'].search(domain)
