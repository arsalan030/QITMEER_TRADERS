from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_brand_pricelist(self):
        """Return the customer's pricelist for this line's product brand, or False."""
        self.ensure_one()
        partner = self.order_id.partner_id.commercial_partner_id
        brand = self.product_id.product_tmpl_id.brand_id
        if not partner or not brand:
            return False
        mapping = partner.brand_pricelist_ids.filtered(
            lambda m: m.brand_id == brand)[:1]
        return mapping.pricelist_id or False

    @api.depends('order_id.partner_id')
    def _compute_pricelist_item_id(self):
        super()._compute_pricelist_item_id()
        for line in self:
            if not line.product_id or line.display_type:
                continue
            pricelist = line._get_brand_pricelist()
            if not pricelist:
                continue  # keep the order's normal pricelist rule
            rule = pricelist._get_product_rule(
                line.product_id,
                quantity=line.product_uom_qty or 1.0,
                uom=line.product_uom_id,
                date=line._get_order_date(),
            )
            if rule:
                line.pricelist_item_id = rule
