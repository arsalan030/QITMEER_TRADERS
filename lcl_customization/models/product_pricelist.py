
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        relation='pricelist_item_product_template_rel',
        column1='pricelist_item_id',
        column2='product_tmpl_id',
        string='Multiple Products',
        check_company=True,
    )

    customer_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='pricelist_item_customer_rel',
        column1='pricelist_item_id',
        column2='partner_id',
        string='Customers',
        check_company=True,
    )

    # --------------------------------------------------
    # COMPUTE APPLIED ON
    # --------------------------------------------------

    @api.depends(
        'categ_id',
        'product_id',
        'product_tmpl_id',
        'product_tmpl_ids',
    )
    def _compute_applied_on(self):
        super()._compute_applied_on()

        for item in self:
            if (
                item.product_tmpl_ids
                and not item.product_tmpl_id
                and not item.product_id
                and not item.categ_id
            ):
                item.applied_on = '1_product'

    # --------------------------------------------------
    # COMPUTE NAME
    # --------------------------------------------------

    @api.depends(
        'applied_on',
        'categ_id',
        'product_tmpl_id',
        'product_id',
        'product_tmpl_ids',
    )
    def _compute_name(self):
        super()._compute_name()

        for item in self:
            if (
                item.product_tmpl_ids
                and not item.product_tmpl_id
                and not item.product_id
                and not item.categ_id
            ):
                item.name = ', '.join(
                    item.product_tmpl_ids.mapped('display_name')
                )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    @api.constrains(
        'product_id',
        'product_tmpl_id',
        'product_tmpl_ids',
        'categ_id',
    )
    def _check_product_consistency(self):
        for item in self:
            if item.product_tmpl_ids and (
                item.product_tmpl_id
                or item.product_id
                or item.categ_id
            ):
                raise ValidationError(
                    'Select either multiple products or a single '
                    'product, variant, or category.'
                )

            if item.product_tmpl_ids:
                continue

            if (
                item.applied_on == '2_product_category'
                and not item.categ_id
            ):
                raise ValidationError('Please select a category.')

            if (
                item.applied_on == '1_product'
                and not item.product_tmpl_id
            ):
                raise ValidationError('Please select a product.')

            if (
                item.applied_on == '0_product_variant'
                and not item.product_id
            ):
                raise ValidationError(
                    'Please select a product variant.'
                )

    # --------------------------------------------------
    # ONCHANGE
    # --------------------------------------------------

    @api.onchange('product_tmpl_ids')
    def _onchange_product_tmpl_ids(self):
        for item in self:
            if item.product_tmpl_ids:
                item.product_tmpl_id = False
                item.product_id = False
                item.categ_id = False

    @api.onchange(
        'product_tmpl_id',
        'product_id',
        'categ_id',
    )
    def _onchange_single_product_selection(self):
        for item in self:
            if (
                item.product_tmpl_id
                or item.product_id
                or item.categ_id
            ):
                item.product_tmpl_ids = False

    # --------------------------------------------------
    # MULTIPLE PRODUCT + MINIMUM QUANTITY MATCHING
    # --------------------------------------------------

    def _is_applicable_for(
            self, product, quantity, *, uom=None, **kwargs
    ):
        self.ensure_one()
        product.ensure_one()

        # 1. CUSTOMER CHECK
        if self.customer_ids:
            partner = kwargs.get('partner')

            if not partner:
                return False

            partner = partner.commercial_partner_id

            allowed_customers = self.customer_ids.mapped(
                'commercial_partner_id'
            )

            if partner not in allowed_customers:
                return False

        # 2. PRODUCT CHECK
        is_multiple_product_rule = bool(
            self.product_tmpl_ids
            and not self.product_tmpl_id
            and not self.product_id
            and not self.categ_id
        )

        if not is_multiple_product_rule:
            return super()._is_applicable_for(
                product,
                quantity,
                uom=uom,
                **kwargs
            )

        # 3. UOM CHECK
        product_uom = product.uom_id
        uom = uom or product_uom

        if self.uom_id and uom != self.uom_id:
            return False

        qty_to_consider = quantity

        if uom not in product_uom + self.uom_id:
            qty_to_consider = uom._compute_quantity(
                quantity,
                product_uom,
            )

        # 4. MINIMUM QUANTITY CHECK
        if (
                self.min_quantity
                and qty_to_consider < self.min_quantity
        ):
            return False

        # 5. MULTIPLE PRODUCT CHECK
        if product._name == 'product.template':
            return product.id in self.product_tmpl_ids.ids

        return (
                product.product_tmpl_id.id
                in self.product_tmpl_ids.ids
        )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    # --------------------------------------------------
    # FIXED PRICE
    # --------------------------------------------------
    @api.depends(
        'product_id',
        'product_uom_id',
        'product_uom_qty',
        'pricelist_item_id',
        'pricelist_item_id.compute_price',
        'pricelist_item_id.fixed_price',
    )
    def _compute_price_unit(self):
        # First execute standard Odoo price calculation
        super()._compute_price_unit()

        for line in self:
            item = line.pricelist_item_id

            if (
                    item
                    and item.compute_price == 'fixed'
                    and line.product_id
            ):
                line.price_unit = item.fixed_price
    # --------------------------------------------------
    # RECOMPUTE PRICELIST RULE ON CUSTOMER CHANGE
    # --------------------------------------------------

    @api.depends(
        'product_id',
        'product_uom_id',
        'product_uom_qty',
        'order_id.partner_id',
        'order_id.pricelist_id',
    )
    def _compute_pricelist_item_id(self):
        for line in self:
            if (
                    not line.product_id
                    or line.display_type
                    or not line.order_id.pricelist_id
            ):
                line.pricelist_item_id = False
                continue

            partner = line.order_id.partner_id

            line.pricelist_item_id = (
                line.order_id.pricelist_id._get_product_rule(
                    product=line.product_id,
                    partner=partner,
                    **line._get_pricelist_kwargs(),
                )
            )

    # --------------------------------------------------
    # RECOMPUTE DISCOUNT
    # --------------------------------------------------

    @api.depends(
        'product_id',
        'product_uom_id',
        'product_uom_qty',
        'pricelist_item_id',
        'order_id.pricelist_id',
        'order_id.partner_id',
    )
    def _compute_discount(self):
        super()._compute_discount()
