from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleBrandRuleWizard(models.TransientModel):
    _name = 'sale.brand.rule.wizard'
    _description = 'Select Price Rule for Sale Order Line'

    line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    product_uom_qty = fields.Float(string='Quantity', readonly=True)
    option_ids = fields.One2many('sale.brand.rule.wizard.option', 'wizard_id')

    def create_from_values(self, partner, product, qty, uom, date, rules, line=False):
        if not rules:
            raise UserError(_("No price rule found for this product in the "
                              "customer's brand pricelists."))
        qty = qty or 1.0
        uom = uom or product.uom_id
        current = line.pricelist_item_id if line else self.env['product.pricelist.item']
        options = []
        for rule in rules:
            currency = rule.pricelist_id.currency_id
            price = rule._compute_price(product, qty, uom, date, currency=currency)
            options.append((0, 0, {
                'rule_id': rule.id,
                'price': price,
                'is_current': rule == current,
            }))
        return self.create({
            'line_id': line.id if line else False,
            'partner_id': partner.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'option_ids': options,
        })

    def _get_action(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Select Price Rule"),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }


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
        if line:
            # Saved line (tag button): write directly.
            if line.order_id.state not in ('draft', 'sent'):
                raise UserError(_("You can only change the price rule on a quotation."))
            line.brand_pricelist_item_id = self.rule_id
            line.with_context(force_price_recomputation=True)._compute_price_unit()
            line._compute_discount()
        # Unsaved line (auto popup): the JS puts the rule on the line itself.
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {
                'brand_rule_id': self.rule_id.id,
                'brand_rule_name': self.rule_id.display_name,
            },
        }
