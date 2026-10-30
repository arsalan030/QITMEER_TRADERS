from odoo import models, fields, api


class SaleOrderLineInternalRef(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('name')
    def _onchange_name_fetch_product_note(self):
        # Agar user ne Description mein kuch type kiya hai
        if self.name:
            search_term = self.name.strip()

            # Product Code (default_code) se product search karein
            product = self.env['product.product'].search(
                [('default_code', '=', search_term)], limit=1
            )

            # Agar exact code mil jaye to product aur uski internal note set karein
            if product:
                self.product_id = product
                self.name = product.description or product.name or ''


# class PurchaseOrderLineInternalRef(models.Model):
#     _inherit = 'purchase.order.line'
#
#     @api.onchange('name')
#     def _onchange_name_fetch_product_note(self):
#         if self.name:
#             search_term = self.name.strip()
#
#             product = self.env['product.product'].search(
#                 [('default_code', '=', search_term)], limit=1
#             )
#
#             if product:
#                 self.product_id = product
#                 self.name = product.description or product.name or ''