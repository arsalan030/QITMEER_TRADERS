from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleBrandRuleWizard(models.TransientModel):
    _name = 'sale.brand.rule.wizard'
    _description = 'Select Price Rule for Sale Order Line'

    line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade')
    product_id = fields.Many2one(related='line_id.product_id')
    product_uom_qty = fields.Float(related='line_id.product_uom_qty')
    option_ids = fields.One2many('sale.brand.rule.wizard.option', 'wizard_id')

    def create_for_line(self, line):
        candidates = line._get_brand_rule_candidates()
        if not candidates:
            raise UserError(_("No price rule found for this product in the "
                              "customer's brand pricelists."))
        product = line.product_id
        qty = line.product_uom_qty or 1.0
        uom = line.product_uom_id or product.uom_id
        date = line._get_order_date()
        options = []
        for rule in candidates:
            currency = rule.pricelist_id.currency_id
            price = rule._compute_price(product, qty, uom, date, currency=currency)
            options.append((0, 0, {
                'rule_id': rule.id,
                'price': price,
                'is_current': rule == line.pricelist_item_id,
            }))
        return self.create({'line_id': line.id, 'option_ids': options})


class SaleBrandRuleWizardOption(models.TransientModel):
    _name = 'sale.brand.rule.wizard.option'
    _description = 'Price Rule Option'
    _order = 'price'

    wizard_id = fields.Many2one('sale.brand.rule.wizard', required=True, ondelete='cascade')
    rule_id = fields.Many2one('product.pricelist.item', string='Price Rule', required=True)
    pricelist_id = fields.Many2one(related='rule_id.pricelist_id', string='Pricelist')
    min_quantity = fields.Float(related='rule_id.min_quantity', string='Min. Qty')
    currency_id = fields.Many2one(related='rule_id.pricelist_id.currency_id')
    price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    is_current = fields.Boolean(string='Applied')

    def action_select(self):
        self.ensure_one()
        line = self.wizard_id.line_id
        if line.order_id.state not in ('draft', 'sent'):
            raise UserError(_("You can only change the price rule on a quotation."))
        line.brand_pricelist_item_id = self.rule_id
        line.with_context(force_price_recomputation=True)._compute_price_unit()
        line._compute_discount()
        return {'type': 'ir.actions.act_window_close'}
