from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    brand_pricelist_item_id = fields.Many2one(
        'product.pricelist.item', string='Selected Price Rule', copy=False,
        help="Price rule chosen manually when the product is covered by more than "
             "one of the customer's brand pricelists.")
    brand_rule_count = fields.Integer(
        compute='_compute_brand_rule_count',
        help="Number of matching price rules in the customer's brand pricelists.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
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

    def _get_brand_rule_from_pricelist(self, pricelist):
        """Return the pricelist rule that applies to this line, as a record."""
        self.ensure_one()
        rule = pricelist._get_product_rule(
            self.product_id,
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom_id,
            date=self._get_order_date(),
        )
        Rule = self.env['product.pricelist.item']
        if not rule:
            return Rule
        return Rule.browse(rule) if isinstance(rule, int) else rule

    def _get_brand_rule_candidates(self):
        """All price rules for this product across the customer's assigned pricelists.

        A pricelist that is NOT mapped to the product's brand is only counted when
        it has a specific rule (product / variant / category), so a catch-all
        "All Products" rule doesn't make every product ambiguous.
        """
        self.ensure_one()
        Rule = self.env['product.pricelist.item']
        partner = self.order_id.partner_id.commercial_partner_id
        if not self.product_id or self.display_type or not partner:
            return Rule
        brand = self.product_id.product_tmpl_id.brand_id
        mappings = partner.brand_pricelist_ids
        rules = Rule
        for pricelist in mappings.pricelist_id:
            rule = self._get_brand_rule_from_pricelist(pricelist)
            if not rule:
                continue
            brand_mapped = brand and brand in mappings.filtered(
                lambda m: m.pricelist_id == pricelist).brand_id
            if not brand_mapped and rule.applied_on == '3_global':
                continue
            rules |= rule
        return rules

    # ------------------------------------------------------------------
    # Computes / onchanges
    # ------------------------------------------------------------------
    @api.depends('product_id', 'product_uom_qty', 'product_uom_id',
                 'order_id.partner_id', 'display_type')
    def _compute_brand_rule_count(self):
        for line in self:
            line.brand_rule_count = len(line._get_brand_rule_candidates())

    @api.depends('order_id.partner_id', 'brand_pricelist_item_id')
    def _compute_pricelist_item_id(self):
        super()._compute_pricelist_item_id()
        for line in self:
            if not line.product_id or line.display_type:
                continue
            # 1) Rule chosen manually in the wizard (if still valid)
            if line.brand_pricelist_item_id:
                if line.brand_pricelist_item_id in line._get_brand_rule_candidates():
                    line.pricelist_item_id = line.brand_pricelist_item_id
                    continue
            # 2) Pricelist mapped to the product's brand
            pricelist = line._get_brand_pricelist()
            if not pricelist:
                continue  # keep the order's normal pricelist rule
            rule = line._get_brand_rule_from_pricelist(pricelist)
            if rule:
                line.pricelist_item_id = rule

    @api.onchange('product_id')
    def _onchange_product_brand_rules(self):
        if not self.product_id:
            return
        self.brand_pricelist_item_id = False
        count = len(self._get_brand_rule_candidates())
        if count > 1:
            return {'warning': {
                'title': _("Several price rules available"),
                'message': _(
                    "%(product)s has %(count)s matching price rules in this customer's "
                    "brand pricelists. Save the line and click the tag icon on it to "
                    "choose which rule to apply.",
                    product=self.product_id.display_name, count=count),
                'type': 'notification',
            }}

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_open_brand_rule_wizard(self):
        self.ensure_one()
        wizard = self.env['sale.brand.rule.wizard'].create_for_line(self)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Select Price Rule"),
            'res_model': 'sale.brand.rule.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
