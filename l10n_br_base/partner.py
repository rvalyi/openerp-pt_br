# -*- encoding: utf-8 -*-

from osv import osv, fields
import re


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'tipo_pessoa': fields.selection([('F', 'Física'), ('J', 'Jurídica')], 'Tipo de pessoa', required=True),
        'cnpj_cpf': fields.char('CNPJ/CPF', size=18),
        'inscr_est': fields.char('Inscr. Estadual', size=16),
        'inscr_mun': fields.char('Inscr. Municipal', size=18),
        'suframa': fields.char('Suframa', size=18),
        'legal_name': fields.char('Razão Social', size=128, help="nome utilizado em documentos fiscais"),
        }
    _defaults = {
        'tipo_pessoa': lambda *a: 'J',
        }

    def _check_cnpj_cpf(self, cr, uid, ids):
        for partner in self.browse(cr, uid, ids):
            if not partner.cnpj_cpf:
                return True

            if partner.tipo_pessoa == 'J':
                return self.validate_cnpj(partner.cnpj_cpf)
            elif partner.tipo_pessoa == 'F':
                return self.validate_cpf(partner.cnpj_cpf)

        return False

    def validate_cnpj(self, cnpj):
        # Limpando o cnpj
        if not cnpj.isdigit():
            cnpj = re.sub('[^0-9]', '', cnpj)

        # verificando o tamano do  cnpj
        if len(cnpj) != 14:
            return False

        # Pega apenas os 12 primeiros dígitos do CNPJ e gera os 2 dígitos que faltam
        cnpj = map(int, cnpj)
        novo = cnpj[:12]

        prod = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        while len(novo) < 14:
            r = sum([x * y for (x, y) in zip(novo, prod)]) % 11
            if r > 1:
                f = 11 - r
            else:
                f = 0
            novo.append(f)
            prod.insert(0, 6)

        # Se o número gerado coincidir com o número original, é válido
        if novo == cnpj:
            return True

        return False

    def validate_cpf(self, cpf):
        if not cpf.isdigit():
            cpf = re.sub('[^0-9]', '', cpf)

        if len(cpf) != 11:
            return False

        # Pega apenas os 9 primeiros dígitos do CPF e gera os 2 dígitos que faltam
        cpf = map(int, cpf)
        novo = cpf[:9]

        while len(novo) < 11:
            r = sum([(len(novo) + 1 - i) * v for i, v in enumerate(novo)]) % 11

            if r > 1:
                f = 11 - r
            else:
                f = 0
            novo.append(f)

        # Se o número gerado coincidir com o número original, é válido
        if novo == cpf:
            return True

        return False

    _constraints = [
        (_check_cnpj_cpf, 'CNPJ/CPF invalido!', ['cnpj_cpf'])
        ]

    _sql_constraints = [
        ('res_partner_cnpj_cpf_uniq', 'unique (cnpj_cpf)', 'Já existe um parceiro cadastrado com este CPF/CNPJ !')
        ]

    def on_change_mask_cnpj_cpf(self, cr, uid, ids, tipo_pessoa, cnpj_cpf):
        if not cnpj_cpf or not tipo_pessoa:
            return {}

        val = re.sub('[^0-9]', '', cnpj_cpf)

        if tipo_pessoa == 'J' and len(val) == 14:
            cnpj_cpf = "%s.%s.%s/%s-%s" % (val[0:2], val[2:5], val[5:8], val[8:12], val[12:14])

        elif tipo_pessoa == 'F' and len(val) == 11:
            cnpj_cpf = "%s.%s.%s-%s" % (val[0:3], val[3:6], val[6:9], val[9:11])

        return {'value': {'tipo_pessoa': tipo_pessoa, 'cnpj_cpf': cnpj_cpf}}

    def zip_search(self, cr, uid, ids, context={}):
        return True

res_partner()


class res_partner_address(osv.osv):
    _inherit = 'res.partner.address'
    _columns = {
        'l10n_br_city_id': fields.many2one('l10n_br_base.city', 'Municipio', domain="[('state_id', '=', state_id)]"),
        'district': fields.char('Bairro', size=32),
        'number': fields.char('Número', size=10),
        }

    def on_change_l10n_br_city_id(self, cr, uid, ids, l10n_br_city_id):
        result = {}

        if not l10n_br_city_id:
            return True

        obj_city = self.pool.get('l10n_br_base.city').read(cr, uid, l10n_br_city_id, ['name', 'id'])
        if obj_city:
            result['city'] = obj_city['name']
            result['l10n_br_city_id'] = obj_city['id']

        return {'value': result}

    def on_change_zip(self, cr, uid, ids, zip):
        result = {'value': {'street': None, 'l10n_br_city_id': None,
                            'city': None, 'state_id': None,
                            'country_id': None, 'zip': None}}

        if not zip:
            return result

        obj_cep = self.pool.get('l10n_br_base.cep').browse(cr, uid, zip)

        result['value']['street'] = obj_cep.street_type + ' ' + obj_cep.street
        result['value']['l10n_br_city_id'] = obj_cep.l10n_br_city_id.id
        result['value']['city'] = obj_cep.l10n_br_city_id.name
        result['value']['state_id'] = obj_cep.state_id.id
        result['value']['country_id'] = obj_cep.state_id.country_id.id
        result['value']['zip'] = obj_cep.code

        return result

res_partner_address()


class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'

    _columns = {
        'acc_number': fields.char('Account Number', size=64, required=False),
        'bank': fields.many2one('res.bank', 'Bank', required=False),
        'acc_number_dig': fields.char("Digito Conta", size=8),
        'bra_number': fields.char("Agência", size=8),
        'bra_number_dig': fields.char("Dígito Agência", size=8),
        }

res_partner_bank()
