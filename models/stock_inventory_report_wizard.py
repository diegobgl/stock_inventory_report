from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para consultar inventario a una fecha pasada'

    date = fields.Date(string='Fecha de consulta', required=True, default=fields.Date.context_today)

    def action_view_inventory_report(self):
        self.ensure_one()

        # Obtener los movimientos de inventario hasta la fecha seleccionada
        stock_moves = self.env['stock.move'].search([('date', '<=', self.date), ('state', '=', 'done')])

        # Procesar datos del inventario
        report_lines = []
        for move in stock_moves:
            product = move.product_id
            location = move.location_dest_id
            quantity = move.product_qty
            unit_cost = product.standard_price if product else 0.0
            total_value = quantity * unit_cost

            # Obtener el ID del lote en lugar de su nombre
            lot_id = None
            if move.move_line_ids and move.move_line_ids[0].lot_id:
                lot_id = move.move_line_ids[0].lot_id.id

            report_lines.append({
                'product_id': product.id if product else False,
                'location_id': location.id if location else False,
                'lot_id': lot_id,  # Asegurarse de que este campo esté configurado para recibir un ID si es Many2one
                'last_move_date': move.date,
                'move_type': 'Compra' if move.picking_type_id.code == 'incoming' else 'Transferencia Interna',
                'quantity': quantity,
                'unit_value': unit_cost,
                'total_value': total_value,
            })

        # Crear registros del reporte
        self.env['stock.inventory.report'].create(report_lines)

        # Mostrar la vista del reporte
        return {
            'type': 'ir.actions.act_window',
            'name': 'Informe de Inventario Histórico',
            'res_model': 'stock.inventory.report',
            'view_mode': 'tree',
            'target': 'current',
        }

    def action_export_inventory_report(self):
        self.ensure_one()

        # Obtener los movimientos de stock hasta la fecha seleccionada
        stock_moves = self.env['stock.move'].search([('date', '<=', self.date), ('state', '=', 'done')])

        # Preparar los datos para el reporte
        inventory_data = []
        for move in stock_moves:
            lot_name = move.move_line_ids[0].lot_id.name if move.move_line_ids and move.move_line_ids[0].lot_id else 'N/A'
            move_type = 'Compra' if move.picking_type_id.code == 'incoming' else 'Transferencia Interna'
            unit_value = move.product_id.standard_price
            total_value = move.product_qty * unit_value

            inventory_data.append({
                'product_name': move.product_id.display_name,
                'location_name': move.location_dest_id.display_name,
                'lot_name': lot_name,
                'last_move_date': move.date,
                'move_type': move_type,
                'quantity': move.product_qty,
                'unit_value': unit_value,
                'total_value': total_value,
            })

        # Crear archivo Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Inventario')
        headers = ['Producto', 'Ubicación', 'Lote/Serie', 'Fecha Último Movimiento', 'Tipo Movimiento', 
                   'Cantidad', 'Valor Unitario', 'Valorizado']

        # Escribir encabezados
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        # Escribir datos en Excel
        row = 1
        for data in inventory_data:
            sheet.write(row, 0, data['product_name'])
            sheet.write(row, 1, data['location_name'])
            sheet.write(row, 2, data['lot_name'])
            sheet.write(row, 3, str(data['last_move_date']))
            sheet.write(row, 4, data['move_type'])
            sheet.write(row, 5, data['quantity'])
            sheet.write(row, 6, data['unit_value'])
            sheet.write(row, 7, data['total_value'])
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()

        # Crear y devolver el archivo adjunto para su descarga
        attachment = self.env['ir.attachment'].create({
            'name': f'Reporte_Inventario_{self.date}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'Reporte_Inventario_{self.date}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Devolver acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }