class MyId(object):
    chain = 'DEFAULT'
    store = 'DEFAULT'

    @classmethod
    def set_id(cls, chain, store):
        cls.chain = chain
        cls.store = store
    
    @classmethod
    def get_id(cls):        
        return '{}-{}'.format(cls.chain, cls.store)

    @classmethod
    def toJSON(cls):
        return {'chain' : cls.chain,
        'store' : cls.store }
