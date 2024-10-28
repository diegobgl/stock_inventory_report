from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

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

        # 1. Obtener el stock inicial en la fecha de inicio
        initial_stock = self.env['stock.quant'].search([
            ('location_id.usage', 'in', ['internal', 'transit']),
            ('quantity', '>', 0),
        ] + domain)

        product_qty = {}
        for quant in initial_stock:
            product_id = quant.product_id.id
            location_id = quant.location_id.id

            if (location_id, product_id) not in product_qty:
                product_qty[(location_id, product_id)] = 0
            product_qty[(location_id, product_id)] += quant.quantity

        # 2. Aplicar las entradas y salidas de stock entre la fecha de inicio y la fecha final
        moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            '|',
            ('location_id.usage', 'in', ['internal', 'transit']),
            ('location_dest_id.usage', 'in', ['internal', 'transit']),
        ] + domain)

        for move in moves:
            product_id = move.product_id.id
            location_id = move.location_id.id
            destination_location_id = move.location_dest_id.id

            # Restar si es una salida de la ubicación interna o tránsito
            if move.location_id.usage in ['internal', 'transit']:
                if (location_id, product_id) not in product_qty:
                    product_qty[(location_id, product_id)] = 0
                product_qty[(location_id, product_id)] -= move.product_uom_qty

            # Sumar si es una entrada a la ubicación interna o tránsito
            if move.location_dest_id.usage in ['internal', 'transit']:
                if (destination_location_id, product_id) not in product_qty:
                    product_qty[(destination_location_id, product_id)] = 0
                product_qty[(destination_location_id, product_id)] += move.product_uom_qty

        # 3. Transformar el resultado en una lista de diccionarios para generar el reporte
        result = []
        for (location_id, product_id), qty in product_qty.items():
            if qty > 0:  # Solo mostrar productos con stock positivo
                result.append({
                    'location_id': self.env['stock.location'].browse(location_id),
                    'product_id': self.env['product.product'].browse(product_id),
                    'quantity': qty,
                })

        return result


    # def _get_stock_moves(self):
    #     # Dominio para filtrar movimientos confirmados entre las fechas seleccionadas
    #     domain = [('state', '=', 'done')]
        
    #     # Aplicar los filtros de fechas
    #     if self.date_from:
    #         domain.append(('date', '>=', self.date_from))
    #     if self.date_to:
    #         domain.append(('date', '<=', self.date_to))
        
    #     # Aplicar los filtros de ubicación (tanto origen como destino)
    #     if self.location_id:
    #         domain.append('|')
    #         domain.append(('location_id', '=', self.location_id.id))  # Salida de la ubicación
    #         domain.append(('location_dest_id', '=', self.location_id.id))  # Entrada a la ubicación
        
    #     # Filtrar por producto
    #     if self.product_id:
    #         domain.append(('product_id', '=', self.product_id.id))

    #     # Buscar movimientos de stock que cumplan con los criterios
    #     moves = self.env['stock.move'].search(domain)
        
    #     # Registrar información de los movimientos encontrados
    #     for move in moves:
    #         move_type = 'Entrada' if move.location_dest_id.id == self.location_id.id else 'Salida'
    #         _logger.info(f"Movimiento: {move_type} | Producto: {move.product_id.name} | Ubicación: {move.location_id.name} -> {move.location_dest_id.name} | Cantidad: {move.product_uom_qty}")

    #     return moves
