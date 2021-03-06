# -*- encoding: utf-8 -*-

from osv import osv, fields
import decimal_precision as dp


class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, order.partner_address_id.id, line.product_id.id, order.partner_id)['taxes']:
                    tax_brw = self.pool.get('account.tax').browse(cr, uid, c['id'])
                    if not tax_brw.tax_code_id.tax_discount:
                        val += c.get('amount', 0.0)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'fiscal_operation_category_id': fields.many2one('l10n_br_account.fiscal.operation.category', 'Categoria', domain="[('type','=','input'),('use_purchase','=',True)]"),
        'fiscal_operation_id': fields.many2one('l10n_br_account.fiscal.operation', 'Operação Fiscal', domain="[('fiscal_operation_category_id','=',fiscal_operation_category_id),(type,'=','input'),('use_purchase','=',True)]"),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Purchase Price'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
                }, multi="sums", help="The amount without tax"),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Purchase Price'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
                }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Purchase Price'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
                }, multi="sums", help="The total amount"),
        }
    _defaults = {
        'invoice_method': 'picking',
        }

    def onchange_partner_id(self, cr, uid, ids, part, company_id=False, fiscal_operation_category_id=False):
        result = super(purchase_order, self).onchange_partner_id(cr, uid, ids, part, company_id)

        if not part or not company_id or not result['value']['partner_address_id'] or not fiscal_operation_category_id:
            result['value']['fiscal_position'] = False
            result['value']['fiscal_operation_id'] = False
            return result

        obj_company = self.pool.get('res.company').browse(cr, uid, [company_id])[0]

        company_addr = self.pool.get('res.partner').address_get(cr, uid, [obj_company.partner_id.id], ['default'])
        company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']])[0]

        from_country = company_addr_default.country_id.id
        from_state = company_addr_default.state_id.id

        obj_partner = self.pool.get('res.partner').browse(cr, uid, [part])[0]
        partner_fiscal_type = obj_partner.partner_fiscal_type_id.id

        if obj_partner.property_account_position:
            result['value']['fiscal_position'] = obj_partner.property_account_position
            result['value']['fiscal_operation_id'] = obj_partner.property_account_position.fiscal_operation_id.id
            result['value']['fiscal_operation_category_id'] = obj_partner.property_account_position.fiscal_operation_id.fiscal_operation_category_id.id
            return result

        partner_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [result['value']['partner_address_id']])[0]

        to_country = partner_addr_default.country_id.id
        to_state = partner_addr_default.state_id.id

        fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('partner_fiscal_type_id','=',partner_fiscal_type),('fiscal_operation_category_id','=',fiscal_operation_category_id)])
        if not fsc_pos_id:
            fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('fiscal_operation_category_id','=',fiscal_operation_category_id)])

        if fsc_pos_id:
            obj_fpo_rule = self.pool.get('account.fiscal.position.rule').browse(cr, uid, fsc_pos_id)[0]
            obj_fpo = self.pool.get('account.fiscal.position').browse(cr, uid, [obj_fpo_rule.fiscal_position_id.id])[0]
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, [obj_fpo.fiscal_operation_id.id])[0]
            result['value']['fiscal_position'] = obj_fpo.id
            result['value']['fiscal_operation_id'] = obj_foperation.id

        return result

    def onchange_partner_address_id(self, cr, uid, ids, partner_address_id, company_id=False, fiscal_operation_category_id=False):
        result = super(purchase_order, self).onchange_partner_address_id(cr, uid, ids, partner_address_id, company_id)

        if not partner_address_id or not company_id:
            result['value']['fiscal_position'] = False
            result['value']['fiscal_operation_id'] = False
            return result

        obj_company = self.pool.get('res.company').browse(cr, uid, [company_id])[0]

        company_addr = self.pool.get('res.partner').address_get(cr, uid, [obj_company.partner_id.id], ['default'])
        company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']])[0]

        from_country = company_addr_default.country_id.id
        from_state = company_addr_default.state_id.id

        partner_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [partner_address_id])[0]

        to_country = partner_addr_default.country_id.id
        to_state = partner_addr_default.state_id.id

        obj_partner = self.pool.get('res.partner').browse(cr, uid, [partner_addr_default.partner_id.id])[0]
        partner_fiscal_type = obj_partner.partner_fiscal_type_id.id
        if obj_partner.property_account_position:
            result['value']['fiscal_position'] = obj_partner.property_account_position
            result['value']['fiscal_operation_id'] = obj_partner.property_account_position.fiscal_operation_id.id
            return result

        fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('partner_fiscal_type_id','=',partner_fiscal_type),('fiscal_operation_category_id','=',fiscal_operation_category_id)])
        if not fsc_pos_id:
            fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('fiscal_operation_category_id','=',fiscal_operation_category_id)])

        if fsc_pos_id:
            obj_fpo_rule = self.pool.get('account.fiscal.position.rule').browse(cr, uid, fsc_pos_id)[0]
            obj_fpo = self.pool.get('account.fiscal.position').browse(cr, uid, [obj_fpo_rule.fiscal_position_id.id])[0]
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, [obj_fpo.fiscal_operation_id.id])[0]
            result['value']['fiscal_position'] = obj_fpo.id
            result['value']['fiscal_operation_id'] = obj_foperation.id

        return result

    def onchange_fiscal_operation_category_id(self, cr, uid, ids, partner_address_id, company_id=False, fiscal_operation_category_id=False):
        result = {'value': {}}

        if not partner_address_id or not company_id or not fiscal_operation_category_id:
            result['value']['fiscal_position'] = False
            result['value']['fiscal_operation_id'] = False
            return result

        obj_company = self.pool.get('res.company').browse(cr, uid, [company_id])[0]

        company_addr = self.pool.get('res.partner').address_get(cr, uid, [obj_company.partner_id.id], ['default'])
        company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']])[0]

        from_country = company_addr_default.country_id.id
        from_state = company_addr_default.state_id.id

        partner_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [partner_address_id])[0]

        to_country = partner_addr_default.country_id.id
        to_state = partner_addr_default.state_id.id

        obj_partner = self.pool.get('res.partner').browse(cr, uid, [partner_addr_default.partner_id.id])[0]
        partner_fiscal_type = obj_partner.partner_fiscal_type_id.id
        if obj_partner.property_account_position:
            result['value']['fiscal_position'] = obj_partner.property_account_position
            result['value']['fiscal_operation_id'] = obj_partner.property_account_position.fiscal_operation_id.id
            return result

        fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('partner_fiscal_type_id','=',partner_fiscal_type),('fiscal_operation_category_id','=',fiscal_operation_category_id)])

        if not fsc_pos_id:
            fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=',company_id), ('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_purchase','=',True),('fiscal_operation_category_id','=',fiscal_operation_category_id)])

        if fsc_pos_id:
            obj_fpo_rule = self.pool.get('account.fiscal.position.rule').browse(cr, uid, fsc_pos_id)[0]
            obj_fpo = self.pool.get('account.fiscal.position').browse(cr, uid, [obj_fpo_rule.fiscal_position_id.id])[0]
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, [obj_fpo.fiscal_operation_id.id])[0]
            result['value']['fiscal_position'] = obj_fpo.id
            result['value']['fiscal_operation_id'] = obj_foperation.id

        return result

    def action_picking_create(self, cr, uid, ids, *args):
        picking_id = False

        for order in self.browse(cr, uid, ids):

            picking_id = super(purchase_order, self).action_picking_create(cr, uid, ids, *args)
            self.pool.get('stock.picking').write(cr, uid, picking_id, {'fiscal_operation_category_id': order.fiscal_operation_category_id.id, 'fiscal_operation_id': order.fiscal_operation_id.id, 'fiscal_position': order.fiscal_position.id})

        return picking_id

purchase_order()


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    _columns = {
        'fiscal_operation_category_id': fields.many2one('l10n_br_account.fiscal.operation.category', 'Categoria', domain="[('type','=','input'),('use_purchase','=',True)]"),
        'fiscal_operation_id': fields.many2one('l10n_br_account.fiscal.operation', 'Operação Fiscal', domain="[('fiscal_operation_category_id','=',fiscal_operation_category_id),('type','=','input'),('use_purchase','=',True)]"),
    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order=False, fiscal_position=False, date_planned=False,
            name=False, price_unit=False, notes=False, fiscal_operation_category_id=False, fiscal_operation_id=False):
        result = super(purchase_order_line, self).product_id_change(
            cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order, fiscal_position, date_planned, name, price_unit, notes)

        if fiscal_operation_category_id:
            result['value']['fiscal_operation_category_id'] = fiscal_operation_category_id

        if fiscal_operation_id:
            result['value']['fiscal_operation_id'] = fiscal_operation_id

        return result

purchase_order_line()
