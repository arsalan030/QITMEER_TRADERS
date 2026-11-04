
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

        is_multiple_product_rule = bool(
            self.product_tmpl_ids
            and not self.product_tmpl_id
            and not self.product_id
            and not self.categ_id
        )

        # Standard Odoo matching for normal rules
        if not is_multiple_product_rule:
            return super()._is_applicable_for(
                product,
                quantity,
                uom=uom,
                **kwargs
            )

        # Product UoM
        product_uom = product.uom_id
        uom = uom or product_uom

        # UoM restriction
        if self.uom_id and uom != self.uom_id:
            return False

        # Convert quantity into product UoM when needed
        qty_to_consider = quantity

        if uom not in product_uom + self.uom_id:
            qty_to_consider = uom._compute_quantity(
                quantity,
                product_uom,
            )

        # Minimum quantity check
        if (
            self.min_quantity
            and qty_to_consider < self.min_quantity
        ):
            return False

        # Product template matching
        if product._name == 'product.template':
            return product.id in self.product_tmpl_ids.ids

        return (
            product.product_tmpl_id.id
            in self.product_tmpl_ids.ids
        )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    
    # --------------------------------------------------
    # DISCOUNT COMPUTATION
    # --------------------------------------------------

    @api.depends(
        'product_id',
        'product_uom_id',
        'product_uom_qty',
        'pricelist_item_id',
        'order_id.pricelist_id',
    )
    def _compute_discount(self):
        # Use Odoo's original discount calculation.
        # It calculates the effective discount from the
        # selected pricelist rule and its base price.
        super()._compute_discount()
