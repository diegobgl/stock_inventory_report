from odoo import models, fields, api

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario a una fecha'

    date_from = fields.Datetime(string="Desde la fecha", required=True)
    date_to = fields.Datetime(string="Hasta la fecha", required=True)
    product_id = fields.Many2one('product.product', string="Producto")
    location_id = fields.Many2one('stock.location', string="Ubicación")
    
    def action_generate_report(self):
        # Limpiar reportes previos
        stock_inventory_report = self.env['stock.inventory.date.report']
        stock_inventory_report.search([]).unlink()

        # Obtener los movimientos combinados en la fecha seleccionada
        combined_moves = self._get_combined_stock_moves()

        # Insertar los resultados en el reporte
        for move in combined_moves:
            stock_inventory_report.create({
                'location_id': move['location_id'].id,
                'product_id': move['product_id'].id,
                'quantity': move['quantity'],
                'lot_name': move.get('lot_name', ''),
                'last_move_date': move.get('last_move_date', None),
                'move_type': move.get('move_type', ''),
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario a Fecha',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.date.report',
            'target': 'main',
        }

    def _get_combined_stock_moves(self):
        """ Obtener los movimientos de stock dentro del rango de fechas """
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.location_id:
            domain.append('|')
            domain.append(('location_id', '=', self.location_id.id))
            domain.append(('location_dest_id', '=', self.location_id.id))

        # Obtener movimientos de stock basados en el dominio anterior
        stock_moves = self.env['stock.move'].search(domain)
        results = {}

        for move in stock_moves:
            for move_line in move.move_line_ids:
                key = (move.product_id.id, move_line.lot_id.id, move.location_id.id)
                
                # Inicializar el registro en el diccionario si no existe
                if key not in results:
                    results[key] = {
                        'location_id': move.location_id,
                        'product_id': move.product_id,
                        'quantity': 0,  # Cantidad total
                        'lot_name': move_line.lot_id.name if move_line.lot_id else 'Sin Lote',
                        'last_move_date': move.date,
                        'move_type': 'Compra' if move.picking_type_id.code == 'incoming' else 'Transferencia Interna',
                    }

                # Sumar o restar las cantidades dependiendo de si es entrada o salida
                if move.location_dest_id.id == self.location_id.id:
                    results[key]['quantity'] += move_line.qty_done  # Entrada
                elif move.location_id.id == self.location_id.id:
                    results[key]['quantity'] -= move_line.qty_done  # Salida

        return results.values()
