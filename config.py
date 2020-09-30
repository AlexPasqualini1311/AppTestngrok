class Config(object):
    SECRET_KEY = "arandomstring"
    HOST = "3b25e486186c.ngrok.io"
    storefrontAccessScopes = 'unauthenticated_read_product_listings,unauthenticated_read_product_tags,unauthenticated_write_checkouts, unauthenticated_read_checkouts,unauthenticated_write_customers, unauthenticated_read_customers,unauthenticated_read_customer_tags,unauthenticated_read_content,'
    adminAccessScopes = "read_content, write_content,read_themes, write_themes,read_products, write_products,read_product_listings,read_customers, write_customers,read_orders, write_orders,read_draft_orders, write_draft_orders,read_inventory, write_inventory,read_locations,read_script_tags, write_script_tags,read_fulfillments, write_fulfillments,read_assigned_fulfillment_orders, write_assigned_fulfillment_orders,read_merchant_managed_fulfillment_orders, write_merchant_managed_fulfillment_orders,read_third_party_fulfillment_orders, write_third_party_fulfillment_orders,read_shipping, write_shipping,read_analytics,read_checkouts, write_checkouts,read_reports, write_reports,read_price_rules, write_price_rules,read_discounts, write_discounts,read_marketing_events, write_marketing_events,read_resource_feedbacks, write_resource_feedbacks,read_shopify_payments_payouts,read_shopify_payments_disputes,read_translations, write_translations,read_locales, write_locales"
    
    SHOPIFY_CONFIG = {
        'API_KEY' :'f26598fad7f4877b1897069d0fcd201b',
        'API_SECRET' :'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',
        'APP_HOME' :'https://'+ HOST,
        'CALLBACK_URI' :'https://' + HOST + '/install',
        'REDIRECT_URI' :'https://' + HOST + '/connect',
        'SCOPE' : storefrontAccessScopes + adminAccessScopes
    }


