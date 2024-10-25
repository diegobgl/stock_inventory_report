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

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo

        moves = self._get_stock_moves()  # Obtener los movimientos basados en los filtros

        for move in moves:
            # Para cada movimiento, iteramos sobre las líneas de movimiento
            for move_line in move.move_line_ids:
                try:
                    # Calcular el valor total basado en la cantidad y el valor unitario
                    unit_value = move.product_id.standard_price
                    total_value = move_line.quantity * unit_value  # Usar el campo correcto de cantidad

                    # Crear el reporte asegurando que los campos Many2one tienen valores válidos
                    stock_inventory_report.create({
                        'product_id': move.product_id.id if move.product_id else False,
                        'location_id': move.location_id.id if move.location_id else False,
                        'quantity': move_line.quantity,  # Asegurarse de usar la cantidad correcta
                        'lot_id': move_line.lot_id.id if move_line.lot_id else False,  # Comprobar si lot_id es válido
                        'date': move.date,
                        'move_type': move.picking_type_id.name if move.picking_type_id else move.reference,
                        'unit_value': unit_value,
                        'total_value': total_value,
                    })

                except AttributeError as e:
                    # Registrar el error y continuar el ciclo sin detener el proceso
                    _logger.error("Error generando reporte para el movimiento %s: %s", move.name, str(e))
                    # Omitir este registro pero continuar el proceso con los siguientes movimientos
                    continue

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
