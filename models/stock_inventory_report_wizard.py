from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para generar reporte de inventario'

    date_from = fields.Date(string="Desde la fecha", required=True)
    date_to = fields.Date(string="Hasta la fecha", required=True)
    location_id = fields.Many2one('stock.location', string="Ubicación", required=False)
    product_id = fields.Many2one('product.product', string="Producto", required=False)

    def action_generate_report(self):
        stock_inventory_report = self.env['stock.inventory.date.report']
        stock_inventory_report.search([]).unlink()  # Limpiar el reporte previo

        quants = self._get_stock_between_dates()  # Obtener stock entre las fechas seleccionadas

        for quant in quants:
            location = quant['location_id']
            product = quant['product_id']
            quantity = quant['quantity']

            # Crear el registro del reporte con los datos obtenidos
            stock_inventory_report.create({
                'location_id': location.id,
                'product_id': product.id,
                'quantity': quantity,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Stock entre Fechas',
            'view_mode': 'tree',
            'res_model': 'stock.inventory.date.report',
            'target': 'main',
        }

    def _get_stock_between_dates(self):
        # Obtenemos las fechas seleccionadas por el usuario
        date_from = self.date_from
        date_to = self.date_to

        # Dominio para ubicaciones internas y de tránsito
        domain = [('location_id.usage', 'in', ['internal', 'transit'])]

        # Filtrar por producto si está seleccionado
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Filtrar por ubicación si está seleccionada
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))

        # Buscar movimientos de stock hasta la fecha de inicio para calcular el stock inicial
        initial_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '<', date_from)  # Movimientos antes de la fecha de inicio para stock inicial
        ] + domain)

        # Buscar movimientos de stock entre la fecha de inicio y la fecha de fin
        moves_between_dates = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)  # Movimientos entre la fecha de inicio y fin
        ] + domain)

        product_qty = {}

        # Calcular el stock inicial antes de la fecha de inicio
        for move in initial_moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            qty_change = move.product_uom_qty if move.location_dest_id.usage in ['internal', 'transit'] else -move.product_uom_qty

            # Inicializar si no está en el diccionario
            if (location_id, product_id) not in product_qty:
                product_qty[(location_id, product_id)] = 0

            # Acumular el stock inicial
            product_qty[(location_id, product_id)] += qty_change

        # Aplicar las entradas y salidas entre las fechas de inicio y fin
        for move in moves_between_dates:
            product_id = move.product_id.id
            location_id = move.location_id.id
            qty_change = move.product_uom_qty if move.location_dest_id.usage in ['internal', 'transit'] else -move.product_uom_qty

            # Inicializar si no está en el diccionario
            if (location_id, product_id) not in product_qty:
                product_qty[(location_id, product_id)] = 0

            # Acumular las entradas y salidas
            product_qty[(location_id, product_id)] += qty_change

        # Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in product_qty.items():
            if qty > 0:  # Solo mostrar productos con stock positivo
                result.append({
                    'location_id': self.env['stock.location'].browse(location_id),
                    'product_id': self.env['product.product'].browse(product_id),
                    'quantity': qty,
                })

        return result


    def _get_stock_moves(self):
        # Dominio para filtrar movimientos confirmados entre las fechas seleccionadas
        domain = [('state', '=', 'done')]
        
        # Aplicar los filtros de fechas, ubicación y producto
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Buscar movimientos de stock que cumplan con los criterios
        moves = self.env['stock.move'].search(domain)
        
        # Registrar información de los movimientos encontrados
        for move in moves:
            _logger.info(f"Move: {move.product_id.name}, Location: {move.location_id.name}, Quantity: {move.product_uom_qty}")

        return moves
