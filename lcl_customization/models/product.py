from odoo import models, fields,api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    reference_note = fields.Text(
        string="Description",
        store=True
    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    reference_note = fields.Text(
        string="REFERENCE NOTE",
        copy=True,
    )

    @api.onchange('product_id')
    def _onchange_product_reference_note(self):
        for line in self:
            if line.product_id:
                line.reference_note = line.product_id.reference_note or False
            else:
                line.reference_note = False


    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        vals['reference_note'] = self.reference_note
        return vals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reference_note = fields.Text(
        string="REFERENCE NOTE",
        copy=True,
    )