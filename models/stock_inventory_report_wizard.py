from odoo import models, fields, api
from datetime import datetime

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario a una fecha con detalles'

    date_to = fields.Date(string="Hasta la fecha", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=False)
    product_id = fields.Many2one('product.product', string="Producto", required=False)

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.date.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo

        # Obtener el stock inicial (incluye quants negativos)
        stock_initial = self._get_initial_stock()

        # Ajustar el stock con los movimientos (incluye salidas y entradas)
        stock_final = self._adjust_stock_with_moves(stock_initial)

        # Crear registros del reporte
        self._create_report_entries(stock_final)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Inventario a Fecha',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.date.report',
            'target': 'main',
        }

    def _get_initial_stock(self):
        """Obtener el stock inicial desde los quants, incluyendo quants negativos"""
        domain_quants = []

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_quants.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_quants.append(('location_id', '=', self.location_id.id))

        # Incluir tanto quants positivos como negativos
        quants = self.env['stock.quant'].search(domain_quants)
        stock_initial = {}
        
        for quant in quants:
            key = (quant.location_id.id, quant.product_id.id)
            if key not in stock_initial:
                stock_initial[key] = {
                    'quantity': 0,
                    'unit_value': quant.product_id.standard_price,
                    'total_value': 0
                }
            stock_initial[key]['quantity'] += quant.quantity
            stock_initial[key]['total_value'] += quant.quantity * quant.product_id.standard_price
        
        return stock_initial

    def _adjust_stock_with_moves(self, stock_initial):
        """Ajustar el stock inicial con los movimientos de entradas y salidas, incluyendo ajustes negativos"""
        date_to = self.date_to
        domain_moves = [('state', '=', 'done'), ('date', '<=', date_to)]

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain_moves.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain_moves.append('|')
            domain_moves.append(('location_id', '=', self.location_id.id))
            domain_moves.append(('location_dest_id', '=', self.location_id.id))

        moves = self.env['stock.move'].search(domain_moves)

        for move in moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Si es una salida (ubicación interna o de tránsito)
            if move.location_dest_id.usage == 'virtual':
                key = (location_id, product_id)
                if key in stock_initial:
                    stock_initial[key]['quantity'] -= move.product_uom_qty
                    stock_initial[key]['total_value'] -= move.product_uom_qty * move.price_unit

            # Si es una entrada desde una ubicación virtual
            elif move.location_id.usage == 'virtual' and move.location_dest_id.usage in ['internal', 'transit']:
                key = (destination_location_id, product_id)
                if key not in stock_initial:
                    stock_initial[key] = {'quantity': 0, 'unit_value': move.price_unit, 'total_value': 0}
                stock_initial[key]['quantity'] += move.product_uom_qty
                stock_initial[key]['total_value'] += move.product_uom_qty * move.price_unit

            # Ajustar para las ubicaciones internas y de tránsito
            if move.location_dest_id.usage in ['internal', 'transit']:
                key = (destination_location_id, product_id)
                if key not in stock_initial:
                    stock_initial[key] = {'quantity': 0, 'unit_value': move.price_unit, 'total_value': 0}
                stock_initial[key]['quantity'] += move.product_uom_qty
                stock_initial[key]['total_value'] += move.product_uom_qty * move.price_unit

            # Si es una salida desde una ubicación interna o de tránsito
            if move.location_id.usage in ['internal', 'transit'] and move.location_dest_id.usage == 'virtual':
                key = (location_id, product_id)
                if key not in stock_initial:
                    stock_initial[key] = {'quantity': 0, 'unit_value': move.price_unit, 'total_value': 0}
                stock_initial[key]['quantity'] -= move.product_uom_qty
                stock_initial[key]['total_value'] -= move.product_uom_qty * move.price_unit

        return stock_initial

    def _create_report_entries(self, stock_final):
        """Crear los registros del reporte en base al stock final calculado"""
        stock_inventory_report = self.env['stock.inventory.date.report']

        for key, values in stock_final.items():
            location_id, product_id = key
            quantity = values['quantity']
            unit_value = values['total_value'] / quantity if quantity > 0 else 0
            stock_inventory_report.create({
                'location_id': location_id,
                'product_id': product_id,
                'quantity': quantity,
                'unit_value': unit_value,
                'total_value': values['total_value'],
            })
