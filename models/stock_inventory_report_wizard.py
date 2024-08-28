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
        records = self.env['stock.inventory.report'].search([('date', '=', self.date)])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Inventario')
        sheet.write(0, 0, 'Producto')
        sheet.write(0, 1, 'Ubicación')
        sheet.write(0, 2, 'Cantidad')
        sheet.write(0, 3, 'Fecha')
        row = 1
        for record in records:
            sheet.write(row, 0, record.product_id.display_name)
            sheet.write(row, 1, record.location_id.display_name)
            sheet.write(row, 2, record.quantity)
            sheet.write(row, 3, str(record.date))
            row += 1
        workbook.close()
        output.seek(0)
        file_data = output.read()
        attachment = self.env['ir.attachment'].create({
            'name': f'Reporte_Inventario_{self.date}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': 'stock.inventory.report.wizard',
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
