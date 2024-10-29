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

        # Obtener el stock inicial hasta la fecha seleccionada
        stock_initial = self._get_initial_stock()

        # Ajustar el stock con los movimientos de entrada y salida
        final_stock = self._get_stock_movements(stock_initial)

        # Insertar los resultados en el reporte
        for record in final_stock:
            stock_inventory_report.create({
                'location_id': record['location_id'],
                'product_id': record['product_id'],
                'quantity': record['quantity'],
                'lot_name': record.get('lot_name', ''),
                'last_move_date': record.get('last_move_date', None),
                'move_type': record.get('move_type', ''),
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario a Fecha',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.date.report',
            'target': 'main',
        }

    def _get_initial_stock(self):
        """ Obtener el stock inicial basado en los quants hasta la fecha de inicio """
        domain = [('create_date', '<=', self.date_from)]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))

        quants = self.env['stock.quant'].search(domain)
        stock_initial = {}

        for quant in quants:
            key = (quant.product_id.id, quant.lot_id.id, quant.location_id.id)
            if key not in stock_initial:
                stock_initial[key] = {
                    'location_id': quant.location_id.id,
                    'product_id': quant.product_id.id,
                    'quantity': quant.quantity,
                    'lot_name': quant.lot_id.name if quant.lot_id else '',
                    'last_move_date': quant.in_date,
                    'move_type': 'Stock Inicial'
                }
        return stock_initial

    def _get_stock_movements(self, stock_initial):
        """ Obtener los movimientos de stock dentro del rango de fechas y ajustar el stock inicial """
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

        stock_moves = self.env['stock.move'].search(domain)

        for move in stock_moves:
            for move_line in move.move_line_ids:
                key = (move.product_id.id, move_line.lot_id.id, move_line.location_id.id)

                # Si el producto está en el stock inicial, ajustamos su cantidad
                if key in stock_initial:
                    if move_line.location_dest_id.id == self.location_id.id:
                        stock_initial[key]['quantity'] += move_line.qty_done  # Entrada
                    elif move_line.location_id.id == self.location_id.id:
                        stock_initial[key]['quantity'] -= move_line.qty_done  # Salida
                else:
                    # Si no está en el stock inicial, lo agregamos como nuevo
                    stock_initial[key] = {
                        'location_id': move_line.location_dest_id.id if move_line.location_dest_id.id == self.location_id.id else move_line.location_id.id,
                        'product_id': move.product_id.id,
                        'quantity': move_line.qty_done if move_line.location_dest_id.id == self.location_id.id else -move_line.qty_done,
                        'lot_name': move_line.lot_id.name if move_line.lot_id else '',
                        'last_move_date': move.date,
                        'move_type': 'Compra' if move.picking_type_id.code == 'incoming' else 'Transferencia Interna',
                    }

        return stock_initial.values()
