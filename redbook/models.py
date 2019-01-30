# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.osv.orm import except_orm
# import openerp.addons.decimal_precision as dp
import logging
import time
from datetime import datetime
import json
import httplib
import httplib2
import hashlib
import json
#import urllib

from zip_data import zip_data


_logger = logging.getLogger(__name__)

zip_data = json.loads(json.dumps(zip_data), encoding = 'UTF-8')


# class redbook(models.Model):
#     _name = 'redbook.redbook'

#     name = fields.Char()

class redbook_config(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'redbook.config'

    PARAMS = [
        ("open_exchange_app_id", "redbook.ex_app_id"),
        ("open_exchange_url", "redbook.ex_url"),
        ("open_exchange_base", "redbook.ex_base"),
    ]

    open_exchange_app_id = fields.Char(string = 'Open Exchange App ID')
    open_exchange_url = fields.Char(string = 'Open Exchange URL')
    open_exchange_base = fields.Char(string = 'Open Exchange Base Currency')
    
    @api.one
    @api.model
    def set_params(self):

        for field_name, key_name in self.PARAMS:
            value = getattr(self, field_name, '').strip()
            self.env['ir.config_parameter'].set_param(key_name, value)


    @api.model
    def get_default_params(self, fields):
        res = {}
        for field_name, key_name in self.PARAMS:
            #_logger.info('\n !!!!!!!!!!!!!!!!!!!!\n %s \n @@@@@@@@@@@@@@@@@@@\n %s', field_name, key_name)
            res[field_name] = self.env['ir.config_parameter'].get_param(key_name, '').strip()
        #_logger.info('\n ++++++++++++++++++++++++res \n %s \n =================', res)
        return res

class redbook_ex_rate(models.Model):
    _name = 'redbook.ex_rate'

    base = fields.Char(string = 'Exchange Rate Base', default = 'USD', required = True)
    source = fields.Char(string = 'Exchange Rate Source', default = 'CNY', required = True)
    target = fields.Char(string = 'Exchange Rate Target', default = 'EUR', required = True)
    b2s = fields.Float(string = 'Base to Source', digits = (12,6))
    b2t = fields.Float(string = 'Base to Target', digits = (12,6))
    s2t = fields.Float(string = 'Source to Target', compute = '_s2t', digits = (12,6))
    manual = fields.Boolean(string = 'Is manual input?')

    _defaults = {
        'base': 'USD',
        'source': 'CNY',
        'target': 'EUR',
        'manual': True
    }
    
    @api.one
    def _s2t(self):
        if (self.b2s and self.b2t):
            self.s2t = self.b2t/self.b2s
        else:
            self.s2t = 1

    @api.model
    @api.depends('source', 'base', 'target')
    def get_online_rate(self):
        #http = httplib2.Http("/opt/odoo/addons/redbook/.cache", disable_ssl_certificate_validation=True)
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        args = []
        conn_params = self.env['redbook.config'].get_default_params(args)
        #_logger.info('XXXXXXXXXXXXXXXXXXXXX %s',conn_params)
        conn_str = conn_params['open_exchange_url']+ '?' + \
                'app_id=' + conn_params['open_exchange_app_id']+ '&base=' + \
                conn_params['open_exchange_base']
        #_logger.info('\n $$$$$ %s', conn_str)

                    
        content = http.request("https://openexchangerates.org/api/latest.json?app_id=076a40c2f7644502a1c89a33a7fbe83e&base=USD", method = "GET")

        #_logger.info('^^^^^^^^^^^^^ \n %s', content)

        return content

    @api.one
    def online_update(self):
        self.get_online_rate()
        #_logger.info('\nSource currency: \n %s', self.source )

        rates = self.get_online_rate()
        a,b = rates
        data = json.loads(b)
        _logger.info('online update rates: %s', rates)
        _logger.info('\n========================online update rates: source %s : %s',
                     self.source ,
                     data['rates'][self.source])
        _logger.info('\n========================online update rates: target %s: %s', 
                     self.target,
                     data['rates'][self.target])
        self.b2s =  data['rates'][self.source]
        self.b2t =  data['rates'][self.target]

        self.manual = False
        pass

    @api.model
    def manual_update(self, args):
        _logger.info('\nmanual update rate: %s')

class redbook_shop(models.Model):
    _name = 'redbook.shop'

    name = fields.Char(required = True, unique = True)
    alias = fields.Char(size = 3, required = True, unique = True)
    app_url = fields.Char()
    app_key = fields.Char()
    app_secret = fields.Char()
    shop_active = fields.Boolean(required = True, default = True)
    partner = fields.Many2one('res.partner', 'Partner')
    default_tax_id = fields.Many2one('account.tax', 'Default Tax')
    # last_import = fields.Datetime(string = 'Last Import');
    last_import_time = fields.Datetime(string = 'Last Import Time')
    last_import_id = fields.Char(string = 'Last Imported Order ID')
    last_import_status = fields.Char(string = 'Last Import Status:')
    
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    
    _defaults = {
        'last_import_time':'2017-08-01 00:00:00'
    }
    
    @api.model
    def get_rb_order(self, order_no, context = None):
        _logger.info("\n++++++++++++++++get_rb_order+++++++++++++++++++++\n")
        res = {}
        now = str(time.time()).split('.')[0]
        package_id = order_no
        api_order = "/ark/open_api/v0/packages"
        url_order = api_order + "/" + package_id
        sign_string =  "/ark/open_api/v0/packages/" \
                + package_id \
                + "?app-key=" \
                + self.app_key \
                + "&timestamp=" + now \
                + self.app_secret
        sign = hashlib.md5(sign_string).hexdigest()

        headers = {
        "timestamp":now,
        "app-key":self.app_key,
        "sign": sign,
        "content-type":"application/json;charset=utf-8"
        }

        conn = httplib.HTTPSConnection(self.app_url)
        #conn = httplib.HTTPConnection(self.app_url)
        conn.request("GET",url_order,headers=headers)
        response = conn.getresponse()
        #_logger.info("\nAPI Order response:\n %s, %s ", response.status, response.read())
        if response.status != 200:
            res['status_ok'] = False
        else:
            data = json.loads(response.read()).get('data')
            #_logger.info(u"\nAPI Order data:\n %s, ", data)
            res.update({'status_ok':True, 'data':data})

        return res

    @api.model
    def get_rb_order_list(self, start_time, context = None):
        _logger.info("\n++++++++++++++++get_rb_order_list+++++++++++++++++++++\n")
        #initial condition
        res = {'status_ok':True, 'data':[]}
        start_time = self.datetime2timestamp(start_time)
        order_list = []
        status_ok = True
        morepages = True
        page_no = 1
        
        api_order_list = "/ark/open_api/v0/packages"

        while morepages and status_ok:
            now = str(time.time()).split('.')[0]
            url_order_list = api_order_list + "?" \
                        + "page_no=" + str(page_no) \
                        + "&start_time=" + str(start_time)
            #_logger.info("url strin: %s", url_order_list)
            sign_string = "/ark/open_api/v0/packages?app-key=" \
                    +self.app_key \
                    + "&page_no=" + str(page_no) \
                    + "&start_time=" + str(start_time) \
                    + "&timestamp="+ str(now)  \
                    + self.app_secret
            #_logger.info("sign string: %s", sign_string)
            sign = hashlib.md5(sign_string).hexdigest()

            headers = {
                "timestamp":now,
                "app-key":self.app_key,
                "sign":sign,
                "content-type":"application/json;charset=utf-8"
            }
            
            conn = httplib.HTTPSConnection(self.app_url)
            #conn = httplib.HTTPConnection(self.app_url)
            conn.request("GET",url_order_list,headers=headers)
            response = conn.getresponse()
            
            #_logger.info("Page: %s, status: %s",page_no, response.status)
            if response.status != 200:
                status_ok = False
                res.update({'status_ok':False})
                _logger.warning("API error, code: %s", response.status)
            else:
                d = response.read()
                data = json.loads(d).get("data")
    
                total_page = int(data.get("total_page"))

                packages = data.get("package_list")
                
                for package in packages:
                    order_list.append({'package_id':package.get("package_id"),
                                       'confirm_time':package.get("confirm_time")})

                page_no = page_no + 1
                if page_no > total_page:
                    morepages = False
                    #_logger.info("\n Order count: %s",len(order_list)) 

        res.update({'data':order_list})




        return res

    
    #@api.model
    #@api.onchange('last_import_status')
    #def check_status(self):
    #    res = {}
    #    if self.last_import_status != 'ok' :
    #        res = {'warning':{
    #            'title':'Import with Error',
    #            'message':self.last_import_status}}
    #    return res

    #@api.one
    @api.model
    def test_function(self, context = None):
        _logger.info("\n++++++++++++++++test function+++++++++++++++++++++\n")
        res = {}

        eans = self.env['redbook.orderline'].search([])
        product_obj = self.env['product.product']
        for ean in eans:
            if product_obj.search_count([['ean13', '=', ean['EAN']]]) == 0:
                product_obj.create({'name':'name_'+ean['EAN'],
                                    'ean13':ean['EAN']})



#        obj = self.env['product.product']
#        rs = obj.search([['ean13','=','6545785675677']])
#        _logger.info("%s", rs.search_count([['ean13','=','6545785675677']]))
#        rs.write({'name':'john'})
        #package_id =self.last_import_id
        
        #order = self.get_rb_order(package_id)
        #if order['status_ok']:
        #    pass
        #else:
        #    _logger.info("import Order Error, Order number: %s", package_id)


        return res


    def datetime2timestamp(self, dt):
        dt1 = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        td = dt1 - datetime(1970, 1, 1)
        timestamp = str(td.total_seconds()).split('.')[0]
        return timestamp

    @api.one
    #@api.model
    def import_order(self,context=None):
        #initial
        _logger.info("\n==================Input Redbook Orders=============================")
        self.last_import_status = 'ok'
        rate_obj = self.env['redbook.ex_rate'].search([], order = 'id desc', limit = 1)
        rate = rate_obj.s2t
        #_logger.info("\nCurrent Rate: %s", rate)

        # Import Orders
        response_order_list = self.get_rb_order_list(self.last_import_time)
        if  not response_order_list['status_ok']:
            _logger.info("\nOrderlist Impport Error!")
            self.last_import_status = 'Error when importing order list!'
        
        else:
            order_list = response_order_list['data'] 
            redbook_order_obj = self.env['redbook.order']
            for package in order_list:
                package_id = package.get("package_id")
                confirm_timestamp = package.get("confirm_time")
                
                order_obj = self.env['redbook.order']
                order_rs = order_obj.search([['name', '=', package_id]]) 
                _logger.info("\nrecord set length: %s", len(order_rs))

                if len(order_rs) == 0:
                
                    response = self.get_rb_order(package_id)
                    if not response['status_ok']:
                        self.last_import_status = 'Error when importing order: ' + package_id
                        break
                    data = response['data']

                    order = order_rs.create({'name':package_id,
                                             'rb_shop_id':self.id,
                                             'rb_shop_package_id':package_id,
                                             'partner':self.partner.id,
                                             'exchange_rate':rate,
                                             'converted':False,
                                             'ship_name': data.get("receiver_name"),
                                             'ship_address1': data.get("receiver_address"),
                                             'ship_address2': data.get("province") + data.get("city") + data.get("district"),
                                             'ship_province': data.get("province"),
                                             'ship_city': data.get("city"),
                                             'ship_district': data.get("district"),
                                             'telephone': data.get("receiver_phone"),
                                             })
                                             
                    order.calculate_zip()


                    for item in data.get("item_list"):
                        #_logger.info("%s", item)
                        order_line = self.env['redbook.orderline'].create({'name':item['item_name'],
                                                                           'order_id':order.id,
                                                                           'EAN':item['barcode'],
                                                                           'description':item['specification'],
                                                                           'qty':item['qty'],
                                                                           'exchange_rate':rate,
                                                                           'rb_price':item['pay_price']})
                    
                    self.last_import_id = package_id
                    self.last_import_time = datetime.fromtimestamp(int(confirm_timestamp))
                    _logger.info("\nLast imported order confirm time: %s", self.last_import_time)
                    


class redbook_orderline(models.Model):
    _name = 'redbook.orderline'

    name = fields.Char()
    order_id = fields.Many2one('redbook.order', 'Order', ondelete= 'cascade', select = True)
    EAN = fields.Char(required = True)
    EAN_ok = fields.Boolean(string = 'EAN OK?')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Char(string = 'Description')
    # qty = fields.Float(string = 'Quantity', digits = dp.get_percision('Product UoS'))
    qty = fields.Float(string = 'Quantity', )
    rb_price = fields.Float(string = 'Origin Price')
    exchange_rate = fields.Float(string = 'Exchange Rate', readonly = True)
    #price = fields.Float(string = 'Price') 
    price = fields.Float(compute = '_compute_price', string = 'Price')

    #@api.onchange('EAN')
    #def set_order_invalid(self):
    #    _logger.info('\n===========get valid %s===========', self.order_id.valid)
    #    self.order_id.write({'valid':False})  
    #    _logger.info('\n===========set valid %s==========+=', self.order_id.valid)

    @api.one
    @api.depends('rb_price', 'exchange_rate')
    def _compute_price(self):
        self.price = self.rb_price * self.exchange_rate 

    #@api.one 
    def set_exchange_rate(self, rate = 1):
        self.exchange_rate = rate

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    district = fields.Char(string = 'District')

   
class product_product(models.Model):
    _inherit = 'product.template'
    
    rb_enable = fields.Boolean(string = "Enabled in Red Book?")
    rb_shop_id = fields.Many2one('redbook.shop', 'Red Book Shop')
    rb_ean = fields.Char(string = "Red Book Barcode")
    rb_name = fields.Char(string = "Red Book Name")
    
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    rb_courier_id = fields.Many2one('redbook.courier_company', 'RB Courier')
    rb_courier_no = fields.Char(string = 'RB courier No')


class redbook_courier_company(models.Model):
    _name = 'redbook.courier_company'
    
    name = fields.Char(string = 'Name')
    code = fields.Char(string = 'Code')


class redbook_order(models.Model):
    _name = 'redbook.order'

    name = fields.Char()
    rb_shop_id = fields.Many2one('redbook.shop', 'Red Book Shop')
    rb_shop_package_id = fields.Char(string = 'Red BooK Order ID')
    orderlines = fields.One2many('redbook.orderline', 'order_id', readonly = True)
    partner = fields.Many2one('res.partner', 'Partner')
    so_id = fields.Many2one('sale.order', 'SO')
    exchange_rate = fields.Float(string = 'Exchange Rate', digits = (12,6), help = 'CNY to Euro')
    converted = fields.Boolean(string = "Converted to SO")
    valid = fields.Boolean(string = "EANs Valid?")
    remove_valid = fields.Boolean(string = "Remove valid when write")
    ship_name = fields.Char(string = 'Ship Address Name')
    ship_id_number = fields.Char(string = 'ID Number')
    ship_address1 = fields.Char(string = 'Ship Address Line 1')
    ship_address2 = fields.Char(string = 'Ship address line 2')
    ship_district = fields.Char(string ='Ship District')
    ship_city = fields.Char(string ='Ship City')
    ship_province = fields.Char(string ='Ship Province')
    ship_country = fields.Char(string ='Ship Country')
    ship_zip = fields.Char(string ='Ship ZIP')
    telephone = fields.Char(string = 'Telephone')
    
    rb_courier_company_id = fields.Many2one('redbook.courier_company', 'Red Book Courier Company')
    rb_courier_no = fields.Char(string = 'Red Book Courier No')
    rb_courier_upload =fields.Boolean(string = "Courier Info uploaded to Red Book?")

    @api.one
    def calculate_zip(self):
        self.ship_zip = '000000'
        
        if self.ship_province[-1] in [u'省', u'市']:
            province = self.ship_province[0: -1]
        else:
            province = self.ship_province
        city = self.ship_city
        district = self.ship_district
        _logger.info(u"p,c,d: %s, %s, %s",province, city, district)
        
        for p in zip_data:
            if p['name'] == province:
                _logger.info(u"found province: %s", p['name'])
                cities = p['child']
                for c in cities:
                    if c['name'] == city:
                        _logger.info(u"found city: %s", c['name'])
                        districts = c['child']
                        for d in districts:
                            if d['name'] == district:
                                _logger.info(u"found district: %s", d['name'])
                                self.ship_zip = d['zipcode']
                        break
                break
        
        
    
    @api.onchange('orderlines')
    def check_orderlines(self):
        self.valid = False
        self.remove_valid = True
        _logger.info("\n===========set valid %s==========-=", self.valid)
        #self.valid_ean()

    @api.one
    def set_exchange_rate(self, rate =1):
        self.exchange_rate = rate
    
    @api.one
    def valid_ean(self):
        v = True
        for item in self.orderlines:
            count = self.env['product.product'].search_count(['|',('ean13', '=', item['EAN']),('rb_ean', '=', item['EAN'])])
            _logger.info('\n imported ean : %s', item['EAN'])
            
            _logger.info('\n ean search count: %s', count )
            #if (not count) or (len(item['EAN']) != 13):
            if (not count):
                v = False
                item['product_id'] = None
            else:
                item['product_id'] = self.env['product.product'].search(['|',('ean13', '=', item['EAN']),('rb_ean', '=', item['EAN'])])     
        self.valid = v

    @api.one
    @api.onchange('exchange_rate')
    def update_rate(self):
        for item in self.orderlines:
            item.write({'exchange_rate':self.exchange_rate})
    
    @api.one
    def update_courier_info(self):
        _logger.info("Update Courier Info. Courier: %s No.:%s", self.rb_courier_company_id.name, self.rb_courier_no)
        if self.rb_courier_company_id.name and self.rb_courier_no:
            conn = httplib.HTTPSConnection(self.rb_shop_id.app_url)
            #conn = httplib.HTTPConnection(self.rb_shop_id.app_url)
            url_str = '/ark/open_api/v0/packages/' + self.name
            now = str(time.time()).split('.')[0]
            sign_string = url_str +'?' \
                        + 'app-key=' + self.rb_shop_id.app_key + '&' \
                        + 'timestamp=' + str(now) \
                        + self.rb_shop_id.app_secret
            sign = hashlib.md5(sign_string).hexdigest()
            
            headers = {
                "timestamp":now,
                "app-key":self.rb_shop_id.app_key,
                "sign": sign,
                "content-type":"application/json;charset=utf-8"
                
            }
            
            body = {
                "status": "shipped",
                "express_company_code": self.rb_courier_company_id.code,
                "express_no": self.rb_courier_no
            }
            
            body_str = json.dumps(body, encoding='utf-8')
            
            conn.request("PUT", url_str, body_str, headers)
            response = conn.getresponse()
            _logger.info("Courier Info update returns status: %s reason: %s", response.status, response.reason)
            conn.close()
            
            if self.so_id:
                self.so_id.rb_courier_id = self.rb_courier_company_id
                self.so_id.rb_courier_no = self.rb_courier_no
            
            self.rb_courier_upload = True
        else:
            _logger.info("!!! Courier Info not ready!!! Courier: %s No.:%s", self.rb_courier_company_id.name, self.rb_courier_no)
            
    '''
    @api.one
    def convert_so(self):
        if self.converted:
            _logger.info("\nSo already exists, can not be converted to SO again. %s", self.name)
            return -1
        self.valid_ean()
        if self.valid:
            province_id = None
            state_obj = self.env['res.country.state']
            province_list = state_obj.search([('name', '=', self.ship_province)], limit = 1)
            if len(province_list) > 0:
                province_id = province_list[0].id
            
            ###### record create address start time#####
            _logger.info('Start creating address object at: %s', str(time.time())) 
            add_obj = self.env['res.partner']
            ship_add = add_obj.create({'name': self.ship_name,
                                       'display_name': self.rb_shop_id.name + u', ' + self.ship_name,
                                       'notify_email': 'none',
                                       'type': 'delivery',
                                       'parent_id': self.rb_shop_id.partner.id,
                                       'street': self.ship_address1,
                                       #'street2': self.ship_address2,
                                       'city': self.ship_city,
                                       'district': self.ship_district,
                                       'zip': self.ship_zip,
                                       'state_id':province_id,
                                       'phone': self.telephone,
                                       'country_id': self.rb_shop_id.partner.country_id.id,
                                       'company_id': 1,
                                       'active': True,
                                       
                                     })
            #_logger.info('\n Ship address: %s', ship_add)
            
            
            ###### record create so start time#####
            _logger.info('Start creating so object at: %s', str(time.time())) 
            so_obj = self.env['sale.order']
            so = so_obj.create({'name':self.rb_shop_id.alias + "_" + self.name,
                                'shop_id':1,
                                'state':'draft',
                                'partner_id':self.rb_shop_id.partner.id,
                                'partner_invoice_id':self.rb_shop_id.partner.address_get(adr_pref = ['invoice'])['invoice'],
                                'partner_order_id':self.rb_shop_id.partner.address_get(adr_pref = ['contact'])['contact'],
                                #'partner_shipping_id':self.rb_shop_id.partner.address_get(adr_pref = ['delivery'])['delivery'],
                                'partner_shipping_id': ship_add.id,
                                'order_policy':'manual',
                                'warehouse_id': self.rb_shop_id.warehouse_id.id,
                               })
            
            ###### record create so line start time#####
            _logger.info('Start creating so line objects at: %s', str(time.time())) 
            if so:
                self.write({'so_id':so.id})
                for item in self.orderlines:
                    sol_obj = self.env['sale.order.line']
                    _logger.info('Start creating so line object for single item at: %s', str(time.time()))
                    sol = sol_obj.create({'order_id':so.id,
                                          'product_id':item.product_id.id,
                                          'price_unit':item.price,
                                          'name':item.product_id.name_get()[0][1],
                                          'product_uom':item.product_id.uom_id.id,
                                          'product_uom_qty':item.qty,
                                          'tax_id':[(6,0,[self.rb_shop_id.default_tax_id.id])]
                                         })
                    self.write({'converted': True})
            _logger.info('So converted at: %s', str(time.time()))
            return 1            
            
        else:
            _logger.info("\nInvalid Red Book Order, can not be converted to SO. %s", self.name)
            return -1
        pass
        '''
        
    @api.one
    def convert_so(self):
        _logger.info('Start RB Order to SO converting at: %s', str(time.time()))
        rb_rec = self.read()
        #_logger.info('Redbook order to dic: \n %s', rb_rec)
        rb_shop_rec = self.rb_shop_id.read()
        rb_partner_rec = self.rb_shop_id.partner.read()
        #rb_partner_obj = self.rb_shop_id.partner
        
        #_logger.info('Redbook partner to dic: \n %s', rb_partner_rec)
        if self.converted:
            _logger.info("\nSo already exists, can not be converted to SO again. %s", self.name)
            return -1
        self.valid_ean()
        
        if self.valid:
            province_id = None
            state_obj = self.env['res.country.state']
            province_list = state_obj.search([('name', '=', self.ship_province)], limit = 1)
            if len(province_list) > 0:
                province_id = province_list[0].id
            
             ###### record create address start time#####
            _logger.info('Start creating address object at: %s', str(time.time()))
            add_obj = self.env['res.partner']
                        
            ship_add = add_obj.create({'name': rb_rec[0]['ship_name'],
                                       'display_name': rb_rec[0]['rb_shop_id'][1] + u', ' + rb_rec[0]['ship_name'],
                                       'notify_email': 'none',
                                       'type': 'delivery',
                                       'parent_id': rb_partner_rec[0]['id'],  #self.rb_shop_id.partner.id,
                                       'street': rb_rec[0]['ship_address1'],
                                       #'street2': self.ship_address2,
                                       'city': rb_rec[0]['ship_city'],
                                       'district': rb_rec[0]['ship_district'],
                                       'zip': rb_rec[0]['ship_zip'],
                                       'state_id':province_id,
                                       'phone': rb_rec[0]['telephone'],
                                       'country_id': rb_partner_rec[0]['country_id'][0], #self.rb_shop_id.partner.country_id.id,
                                       'company_id': 1,
                                       'active': True,
                                       
                                     })
            #_logger.info('\n Ship address: %s', ship_add)
            
            ###### record create so start time#####
            
            _logger.info('Start creating so object at: %s', str(time.time())) 
            
            so_obj = self.env['sale.order']
            
            #time1 = time.time()
            #invoice_address = rb_partner_obj.address_get(adr_pref = ['invoice'])['invoice'],
            #time2 = time.time()
            
            #_logger.info('Time to get invoice address: %s', str(time2 - time1))
            so = so_obj.create({'name':rb_shop_rec[0]['alias'] + "_" + rb_rec[0]['name'],
                                #'shop_id':1,
                                'state':'draft',
                                'partner_id':rb_partner_rec[0]['id'],     #self.rb_shop_id.partner.id,
                                'partner_invoice_id': rb_partner_rec[0]['id'],   #invoice_address,   #rb_partner_obj.address_get(adr_pref = ['invoice'])['invoice'],
                                #'partner_order_id':self.rb_shop_id.partner.address_get(adr_pref = ['contact'])['contact'],
                                #'partner_shipping_id':self.rb_shop_id.partner.address_get(adr_pref = ['delivery'])['delivery'],
                                'partner_shipping_id': ship_add.id,
                                'order_policy':'manual',
                                'warehouse_id': rb_shop_rec[0]['warehouse_id'][0] #self.rb_shop_id.warehouse_id.id,
                               })
                               
             ###### record create so line start time#####
            _logger.info('Start creating so line objects at: %s', str(time.time())) 
            if so:
                so_id = so.id
                self.write({'so_id':so_id})
                
                for item in self.orderlines:
                    item_rec = item.read()
                    prod_rec = item.product_id.read()
                    #_logger.info('prod_rec: \n %s', rb_partner_rec)

                    sol_obj = self.env['sale.order.line']
                    _logger.info('Start creating so line object for single item at: %s', str(time.time()))
                    sol = sol_obj.create({'order_id':so_id,
                                          'product_id':item_rec[0]['product_id'][0],    #item.product_id.id,
                                          'price_unit':item_rec[0]['price'],    #item.price,
                                          'name':prod_rec[0]['name'],    #item.product_id.name_get()[0][1],
                                          'product_uom':prod_rec[0]['uom_id'][0], #item.product_id.uom_id.id,
                                          'product_uom_qty':item_rec[0]['qty'],
                                          'tax_id':[(6,0,[rb_shop_rec[0]['default_tax_id'][0]])]     #[(6,0,[self.rb_shop_id.default_tax_id.id])]
                                         })
                    self.write({'converted': True})
            _logger.info('So converted at: %s', str(time.time()))
            return 1
        else:
            _logger.info("\nInvalid Red Book Order, can not be converted to SO. %s", self.name)
            return -1
        pass


class redbook_inventory_uploader(models.Model):
    _name = 'redbook.inventory_uploader'
    
    def upload_inv(self, cr, uid, context=None):
        prod_obj = self.pool.get('product.product')
        prod_ids = prod_obj.search(cr, uid, [('rb_enable', '=', True)])
        #rb_shop_obj = self.pool.get('product.product')
        for prod_id in prod_ids:
            if prod_obj.browse(cr, uid, prod_id, context=context)['rb_ean']:
                ean = prod_obj.browse(cr, uid, prod_id, context=context)['rb_ean']
            else:
                ean = prod_obj.browse(cr, uid, prod_id, context=context)['ean13']
            qty = prod_obj.browse(cr, uid, prod_id, context=context)['virtual_available']
            _logger.info('type of qty: %s', type(qty))
            if qty < 0:
                qty = 0
            rb_shop = prod_obj.browse(cr, uid, prod_id, context=context)['rb_shop_id']
            
            shop_name = rb_shop[0].name
            app_url = rb_shop[0].app_url
            app_key = rb_shop[0].app_key
            app_secret =rb_shop[0].app_secret
            
            _logger.info(u"cron: ean: %s qty: %s shop name %s shop_url: %s key: %s secret: %s", ean, qty, shop_name, app_url, app_key, app_secret)
            
            url_str = '/ark/open_api/v0/inventories/' + ean
            now = str(time.time()).split('.')[0]
            sign_string = url_str +'?' \
                        + 'app-key=' + app_key + '&' \
                        + 'timestamp=' + str(now) \
                        + app_secret
            sign = hashlib.md5(sign_string).hexdigest()
            
            headers = {
                "timestamp":now,
                "app-key":app_key,
                "sign": sign,
                "content-type":"application/json;charset=utf-8"
                
            }
            
            body = {
                "qty": qty
            }
            
            body = json.dumps(body, encoding="utf-8")
            
            conn = httplib.HTTPSConnection(app_url)
            #conn = httplib.HTTPConnection(app_url)
            conn.request("PUT", url_str, body, headers)
            response = conn.getresponse()
            _logger.info("inv update returns status: %s reason: %s", response.status, response.reason)
            conn.close()
            
            '''
            u_str = '/ark/open_api/v0/express_companies'
            now = str(time.time()).split('.')[0]
            sign_string = u_str +'?' \
                        + 'app-key=' + app_key + '&' \
                        + 'timestamp=' + str(now) \
                        + app_secret
            sign = hashlib.md5(sign_string).hexdigest()
            headers = {
                "timestamp":now,
                "app-key":app_key,
                "sign": sign,
                "content-type":"application/json;charset=utf-8"
                }
            conn = httplib.HTTPConnection(app_url)
            conn.request("GET", u_str, headers = headers)
            _logger.info("response type: %s", type(conn))
            response = conn.getresponse()
            _logger.info("response type: %s", type(response))
            _logger.info("courier queue returns status: %s reason: %s", response.status, response.reason)
            _logger.info(u"couriers: %s", response.read())
            conn.close()
            break
            '''
                

    


# class redbook_importline(models.Model):
#     _name = 'redbook.importline'
# 
#     name = fields.Char()
#     
