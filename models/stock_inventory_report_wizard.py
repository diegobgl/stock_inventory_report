import base64
import io
import xlsxwriter
from odoo import models, fields

class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Wizard para consultar inventario a una fecha pasada'

    date = fields.Date(string='Fecha de consulta', required=True, default=fields.Date.context_today)

    def action_view_inventory_report(self):
        self.ensure_one()
        self.env['stock.inventory.report'].generate_report(self.date)
        action = self.env.ref('stock_inventory_report.action_stock_inventory_report').read()[0]
        action['context'] = {'default_date': self.date}
        return action

    def action_export_inventory_report(self):
        self.ensure_one()

        # Obtener los movimientos de stock hasta la fecha seleccionada
        stock_moves = self.env['stock.move'].search([('date', '<=', self.date), ('state', '=', 'done')])

        # Preparar los datos para el reporte
        inventory_data = {}
        for move in stock_moves:
            key = (move.product_id.id, move.location_id.id)
            if key not in inventory_data:
                inventory_data[key] = 0
            if move.location_dest_id.id == move.location_id.id:
                inventory_data[key] += move.product_qty
            else:
                inventory_data[key] -= move.product_qty

        # Crear archivo Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Inventario')
        sheet.write(0, 0, 'Producto')
        sheet.write(0, 1, 'Ubicación')
        sheet.write(0, 2, 'Cantidad')
        sheet.write(0, 3, 'Fecha')

        # Escribir datos en Excel
        row = 1
        for (product_id, location_id), quantity in inventory_data.items():
            sheet.write(row, 0, self.env['product.product'].browse(product_id).display_name)
            sheet.write(row, 1, self.env['stock.location'].browse(location_id).display_name)
            sheet.write(row, 2, quantity)
            sheet.write(row, 3, str(self.date))
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()

        # Crear y devolver el archivo adjunto para su descarga
        return {
            'type': 'ir.actions.act_url',
            'url': f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{base64.b64encode(file_data).decode()}',
            'target': 'new',
        }
