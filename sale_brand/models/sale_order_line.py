from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    brand_pricelist_item_id = fields.Many2one(
        'product.pricelist.item', string='Selected Price Rule', copy=False,
        help="Price rule chosen in the wizard when the product is priced in more "
             "than one of the customer's brand pricelists.")
    brand_rule_count = fields.Integer(
        compute='_compute_brand_rule_count',
        help="Number of matching price rules in the customer's brand pricelists.")

    # ------------------------------------------------------------------
    # Rule lookup (usable without a saved line, e.g. from the JS popup)
    # ------------------------------------------------------------------
    @api.model
    def _brand_rule_from_pricelist(self, pricelist, product, qty, uom, date):
        rule = pricelist._get_product_rule(
            product, quantity=qty or 1.0, uom=uom or product.uom_id, date=date)
        Rule = self.env['product.pricelist.item']
        if not rule:
            return Rule
        return Rule.browse(rule) if isinstance(rule, int) else rule

    @api.model
    def _brand_rule_candidates(self, partner, product, qty, uom, date):
        """Every price rule for `product` in the pricelists assigned to `partner`.

        A pricelist not mapped to the product's brand only counts when it has a
        rule for this product / variant / category, so a catch-all
        "All Products" rule does not make every product ambiguous.
        """
        Rule = self.env['product.pricelist.item']
        partner = partner.commercial_partner_id
        if not partner or not product:
            return Rule
        brand = product.product_tmpl_id.brand_id
        mappings = partner.brand_pricelist_ids
        rules = Rule
        for pricelist in mappings.pricelist_id:
            rule = self._brand_rule_from_pricelist(pricelist, product, qty, uom, date)
            if not rule:
                continue
            brand_mapped = bool(brand) and brand in mappings.filtered(
                lambda m: m.pricelist_id == pricelist).brand_id
            if not brand_mapped and rule.applied_on == '3_global':
                continue
            rules |= rule
        return rules

    def _get_brand_rule_candidates(self):
        self.ensure_one()
        if not self.product_id or self.display_type:
            return self.env['product.pricelist.item']
        return self._brand_rule_candidates(
            self.order_id.partner_id, self.product_id, self.product_uom_qty,
            self.product_uom_id, self._get_order_date())

    def _get_brand_pricelist(self):
        """Default pricelist for this line's brand (first mapping), or False."""
        self.ensure_one()
        partner = self.order_id.partner_id.commercial_partner_id
        brand = self.product_id.product_tmpl_id.brand_id
        if not partner or not brand:
            return False
        mapping = partner.brand_pricelist_ids.filtered(
            lambda m: m.brand_id == brand)[:1]
        return mapping.pricelist_id or False

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
            # 1) Rule chosen in the wizard (if still valid for this line)
            chosen = line.brand_pricelist_item_id
            if chosen and chosen in line._get_brand_rule_candidates():
                line.pricelist_item_id = chosen
                continue
            # 2) Pricelist mapped to the product's brand
            pricelist = line._get_brand_pricelist()
            if not pricelist:
                continue  # keep the order's normal pricelist rule
            rule = line._brand_rule_from_pricelist(
                pricelist, line.product_id, line.product_uom_qty,
                line.product_uom_id, line._get_order_date())
            if rule:
                line.pricelist_item_id = rule

    # Standard Odoo only recomputes price/discount on product, UoM or qty change:
    # also recompute them when a rule is picked in the wizard.
    @api.depends('brand_pricelist_item_id')
    def _compute_price_unit(self):
        return super()._compute_price_unit()

    @api.depends('brand_pricelist_item_id')
    def _compute_discount(self):
        return super()._compute_discount()

    @api.onchange('product_id')
    def _onchange_product_reset_brand_rule(self):
        self.brand_pricelist_item_id = False

    # ------------------------------------------------------------------
    # Wizard
    # ------------------------------------------------------------------
    @api.model
    def get_brand_rule_wizard(self, partner_id, product_id, qty=1.0, uom_id=False, date=False):
        """Called from the order line product field right after a product is picked.

        Returns the id of a wizard to open, or False when there is 0 or 1 rule.
        """
        partner = self.env['res.partner'].browse(partner_id)
        product = self.env['product.product'].browse(product_id)
        uom = self.env['uom.uom'].browse(uom_id) if uom_id else product.uom_id
        date = fields.Datetime.to_datetime(date) if date else fields.Datetime.now()
        candidates = self._brand_rule_candidates(partner, product, qty, uom, date)
        if len(candidates) < 2:
            return False
        wizard = self.env['sale.brand.rule.wizard'].create_from_values(
            partner, product, qty, uom, date, candidates)
        return wizard.id

    def action_open_brand_rule_wizard(self):
        """Tag button on a saved line: re-open the choice."""
        self.ensure_one()
        wizard = self.env['sale.brand.rule.wizard'].create_from_values(
            self.order_id.partner_id, self.product_id, self.product_uom_qty,
            self.product_uom_id, self._get_order_date(),
            self._get_brand_rule_candidates(), line=self)
        return wizard._get_action()
