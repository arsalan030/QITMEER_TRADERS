import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";

/**
 * When a product is picked on a sale order line and it is priced in more than one
 * of the customer's brand pricelists, open the "Select Price Rule" wizard and put
 * the chosen rule on the line.
 *
 * The component is taken from the field registry (not imported by path) because
 * its file moved between Odoo 19.0 and later builds.
 */
const SaleOrderLineProductField = registry
    .category("fields")
    .get("sol_product_many2one").component;

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        this.brandRuleOrm = useService("orm");
        this.brandRuleAction = useService("action");
    },

    async _onProductUpdate() {
        await super._onProductUpdate(...arguments);
        try {
            await this._openBrandRuleWizard();
        } catch {
            // Never block product selection (or other modules' tests) if the
            // lookup fails: the line simply keeps its default price rule.
        }
    },

    async _openBrandRuleWizard() {
        const line = this.props.record;
        const order = line.model.root.data;
        const productId = line.data.product_id?.id;
        const partnerId = order.partner_id?.id;
        if (!productId || !partnerId) {
            return;
        }
        const wizardId = await this.brandRuleOrm.call(
            "sale.order.line",
            "get_brand_rule_wizard",
            [
                partnerId,
                productId,
                line.data.product_uom_qty || 1.0,
                line.data.product_uom_id?.id || false,
                order.date_order ? serializeDateTime(order.date_order) : false,
            ]
        );
        if (!wizardId) {
            return;
        }
        await this.brandRuleAction.doAction(
            {
                type: "ir.actions.act_window",
                name: "Select Price Rule",
                res_model: "sale.brand.rule.wizard",
                res_id: wizardId,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: async (info) => {
                    if (info && info.brand_rule_id) {
                        await line.update({
                            brand_pricelist_item_id: {
                                id: info.brand_rule_id,
                                display_name: info.brand_rule_name,
                            },
                        });
                    }
                },
            }
        );
    },
});
