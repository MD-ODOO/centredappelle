# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import logging

log = logging.getLogger(__name__)

# =========================================
# Enfant
# =========================================
class HrEmployeeChild(models.Model):
    _name = 'hr.employee.child'
    # _inherit = ['document.files']
    _description = "Enfant de l'employé"

 
    name = fields.Char(string="Prénom", required=True)
    date_of_birth = fields.Date(string='Date de naissance', required=True)
    employee_id = fields.Many2one('hr.employee', string="Employé", ondelete='cascade')
    gender = fields.Selection([('male','Masculin'),('female','Féminin')], string='Genre')
    deceased = fields.Boolean(string='Décédé(e)')
    infirm = fields.Boolean(string='Infirme')
    adopted = fields.Boolean(string='Adopté(e)')

    age_int = fields.Integer(string="Âge Employé", compute="_compute_age", store=True)
    age = fields.Char(
    string="Âge",
    compute="_compute_age_display",
    readonly=True) 
    
    no_twenty_one = fields.Boolean(string="A plus de 21 ans", compute="_compute_is_over_21", store=True)
    supported = fields.Boolean(string="Pris(e) en charge ?", compute='_compute_is_supported', store=True)

    document_ids = fields.Many2many(
        'hr.employee.document',
        'child_document_rel',
        'child_id',
        'document_id',
        string="Documents justificatifs"
    )
    document_count = fields.Integer(string="Documents", compute="_compute_document_count", store=True)

    justificatif = fields.Boolean(
        string="Justificatif Validé",
        default=False,
    )
    justificatif_readonly = fields.Boolean(
        string="Justificatif verrouillé",
        compute='_compute_justificatif_readonly',
        store=True
    )

    # ----------------------------------------------------
    # COMPUTE
    # ----------------------------------------------------
   # @api.depends('date_of_birth')
   # def _compute_age(self):
    #    today = date.today()
     #   for rec in self:
      #      if rec.date_of_birth:
       #         delta = relativedelta(today, rec.date_of_birth)
        #        rec.age_int = delta.years
         #       rec.age = f"{delta.years}"
          #  else:
           #     rec.age_int = 0
            #    rec.age = "0 an"
    
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age_int = relativedelta(today, rec.date_of_birth).years
            else:
                rec.age_int = 0
                
    def _compute_age_display(self):
        for rec in self:
            rec.age = f"{rec.age_int}" if rec.age_int else "0"

    @api.depends('date_of_birth')
    def _compute_is_over_21(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.no_twenty_one = relativedelta(today, rec.date_of_birth).years > 21
            else:
                rec.no_twenty_one = False
    
    

    @api.depends('no_twenty_one','justificatif')
    def _compute_is_supported(self):
        for rec in self:
            rec.supported = not (rec.no_twenty_one and not rec.justificatif)

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('document_ids')
    def _compute_justificatif_readonly(self):
        for rec in self:
            rec.justificatif_readonly = not bool(rec.document_ids)

    # ----------------------------------------------------
    # ACTIONS
    # ----------------------------------------------------
    def action_open_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('employee_ref_id', '=', self.id)],
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref_id': %s}" % self.id
        }

    # ----------------------------------------------------
    # CONTRAINTES / WRITE
    # ----------------------------------------------------
   
    # ----------------------------------------------------
    # DISPLAY NAME
    # ----------------------------------------------------
    def name_get(self):
        return [(rec.id, f"{rec.firstname} {rec.name}".strip()) for rec in self]


# =========================================
# Conjointe / Femme
# =========================================
class HrEmployeeHusband(models.Model):
    _name = 'hr.employee.husband'
    # _inherit = ['documents.mixin']
    _description = "Femme de l'employé"


    name = fields.Char(string="Prénom et NOM", required=True)
    holder_of_disability_pension = fields.Boolean(string="Conjointe Avec Revenu ?", default=True)
    employee_id = fields.Many2one('hr.employee', string="Employé", ondelete='cascade')
    date_of_birth = fields.Date(string='Date de naissance', required=True)
    gender = fields.Selection([('male','Masculin'),('female','Féminin')], string='Genre')

    document_ids = fields.One2many(
        'hr.employee.document',
        'employee_ref_id',
        domain=lambda self: [('res_model','=',self._name)],
        string="Documents"
    )
    document_count = fields.Integer(string="Nbr Doc", compute="_compute_document_count", store=True)
    
    date_mariage = fields.Date(string='Date de Mariage')

    # ----------------------------------------------------
    # COMPUTE
    # ----------------------------------------------------
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    # ----------------------------------------------------
    # ACTIONS
    # ----------------------------------------------------
    
        
    def action_open_income_justification(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('employee_ref_id', '=', self.id)],
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref_id': %s}" % self.id
        }
    
    def action_open_marriage_certificate(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('employee_ref_id', '=', self.id)],
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref_id': %s}" % self.id
        }
   

    # ----------------------------------------------------
    # CONTRAINTES
    # ----------------------------------------------------
   

    # ----------------------------------------------------
    # DISPLAY NAME
    # ----------------------------------------------------
    def name_get(self):
        return [(rec.id, f"{rec.firstname} {rec.name}".strip()) for rec in self]
