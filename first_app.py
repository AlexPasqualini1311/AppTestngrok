from flask import Flask, render_template, request, redirect, Response, session
from config import Config as cfg

from sgqlc.endpoint.http import HTTPEndpoint

import requests
import json
import sys


app = Flask(__name__, template_folder="templates")
app.debug = True
app.secret_key = cfg.SECRET_KEY

def get_storefront_access_tokens():
    headers = {
            "X-Shopify-Access-Token": session.get("access_token"),
            "Content-Type": "application/graphql",
            "Accept": "application/json",
        }
    url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])
    
    query='''
    {
        shop{
            storefrontAccessTokens(first:100){
                edges{
                    node{
                        accessToken
                        id
                    }
                }
            }
        }
    }
    '''

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query)

    nodes = data["data"]["shop"]["storefrontAccessTokens"]["edges"][:]
    if len(nodes)==0:
        return []
    else:
        tokens=[]
        for dic in nodes:
            tokens.append({
                "token":dic["node"]["accessToken"],
                "id": dic["node"]["id"],
                })
        return tokens

def create_storefront_token():
    headers = {
            "X-Shopify-Access-Token": session.get("access_token"),
            "Content-Type": "application/graphql",
            "Accept": "application/json",
    }
    url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])
    query='''
    mutation storefrontAccessTokenCreate($input: StorefrontAccessTokenInput!) {
        storefrontAccessTokenCreate(input: $input) {
            shop {
                id
            }
            storefrontAccessToken {
                id
                accessToken
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    variables={
        "input": {
            "title":"storefront_access"
        }
    }

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query,variables)
    response=data

    return response["data"]["storefrontAccessTokenCreate"]["storefrontAccessToken"]["accessToken"]

def delete_token(token):
    headers = {
                "X-Shopify-Access-Token": session.get("access_token"),
                "Content-Type": "application/graphql",
                "Accept": "application/json",
    }
    url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])

    query='''
    mutation storefrontAccessTokenDelete($input: StorefrontAccessTokenDeleteInput!) {
        storefrontAccessTokenDelete(input: $input) {
            deletedStorefrontAccessTokenId
            userErrors {
                field
                message
            }
        }
    }
    '''
    for dic in token[:-1]:
        variable={
            "input":{
                "id":dic["id"]
            }
        }

        endpoint=HTTPEndpoint(url, headers)
        data=endpoint(query,variable)

        print(data.get("data",False))
    return token[-1]

def get_registered_webhooks_for_shop():
    headers = {
        "X-Shopify-Access-Token": session.get("access_token"),
        "Content-Type": "application/json"
    }

    url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])

    query='''
        {
            webhookSubscriptions(first:10){
                edges{
                    node{
                        id
                        topic
                        callbackUrl
                    }
                }
            }
        }
    '''

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query)

    nodes = data["data"]["webhookSubscriptions"]["edges"][:]
    if len(nodes)==0:
        return None
    else:
        webhooks=[]
        for node in nodes:
            webhooks.append({
                "address": node["node"]["callbackUrl"],
                "topic": node["node"]["topic"],
                "id": node["node"]["id"],
            })
        return webhooks

def create_cart(token):
    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }
    query ='''
        mutation checkoutCreate($input: CheckoutCreateInput!) {
            checkoutCreate(input: $input) {
                checkout {
                id
                }
                checkoutUserErrors {
                    code
                    field
                    message
                }
            }
        }
        '''

    query_associate_customer='''
        mutation checkoutCustomerAssociateV2($checkoutId: ID!, $customerAccessToken: String!) {
            checkoutCustomerAssociateV2(checkoutId: $checkoutId, customerAccessToken: $customerAccessToken) {
                checkout {
                    id
                }
                checkoutUserErrors {
                    code
                    field
                    message
                }
                customer {
                    id
                }
            }
        }
    '''

    variables = {
        "input":{}
    }

    endpoint = HTTPEndpoint(url,headers)
    data=endpoint(query, variables)

    with open("create_checkout.json","w") as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)

    with open("create_checkout.json","r") as f:
        response = json.load(f)
        checkout_id = response["data"]["checkoutCreate"]["checkout"]["id"]

        variables_associate_customer={
            'checkoutId':checkout_id,
            'customerAccessToken':token,
        }

        endpoint_associate_customer=HTTPEndpoint(url,headers)
        endpoint_associate_customer(query_associate_customer,variables_associate_customer)

@app.route('/scope', methods=['GET'])
def scopes():
    liste=session.get('scopes').split(',')
    print(liste)
    return render_template("scopes.html", liste=liste)

@app.route('/webhooks', methods=['GET', 'POST'])
def webhooks():
    if request.method == "GET":
        if get_registered_webhooks_for_shop():
            return render_template('webhooks.html',
                                webhooks=get_registered_webhooks_for_shop())
        else:
            return render_template('webhooks.html',vide=True)
    else:
        webhook_data = json.loads(request.data)
        print("request: {0}".format(webhook_data))
        return Response(status=200)

@app.route('/webhook_form',methods=['GET'])
def webhook_form():
    return render_template('webhook_form.html')

@app.route('/register_webhook', methods=['GET','POST'])
def register_webhook():

    info={}
    for key,value in request.form.items():
        info[key]=value
    
    print("info : ",info)

    if info["method"]=="post":
        ### post request ###
        headers = {
            "X-Shopify-Access-Token": session.get("access_token"),
            "Content-Type": "application/json"
        }

        payload = {
            "webhook": {
                "topic": info["topic"].casefold().replace("_","/"),
                "address": "https://{0}/webhooks".format(cfg.HOST),
                "format": "json"
            }
        }

        response = requests.post("https://" + session.get("shop")
                                + "/admin/webhooks.json",
                                data=json.dumps(payload), headers=headers)
        print("response : ",response)

        if response.status_code == 201:

            return render_template('register_webhook.html',
                                method="Post Request",webhook_response=json.loads(response.text))
        else:
            return Response(response="{0} - {1}".format(response.status_code,
                                                        response.text), status=200)
    else:
    ### graphQL mutation ###
        headers = {
            "X-Shopify-Access-Token": session.get("access_token"),
            "Content-Type": "application/graphql",
            "Accept": "application/json",
        }
        url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])

        query='''
        mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
            webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
                userErrors {
                    field
                    message
                }
                webhookSubscription {
                    id
                    topic
                    format
                }
            }
        }
        '''

        variables={
            "topic": info["topic"],
            "webhookSubscription": {
                "callbackUrl": "https://{0}/webhooks".format(cfg.HOST),
                "format": "JSON",
            }
        }

        endpoint=HTTPEndpoint(url,headers)
        data=endpoint(query,variables)

        with open('webhook_subscription.json','w') as f:
            json.dump(data, f, sort_keys=True, indent=2, default=str)
        
        with open('webhook_subscription.json') as f:
            response=json.load(f)
            print("response : ",response)
            if response.get("data").get("webhookSubscriptionCreate"):
                webhook=response["data"]["webhookSubscriptionCreate"]["webhookSubscription"]

                return render_template('register_webhook.html',
                                method="graphQL",webhook_response=webhook)
            
            else:
                return render_template('error.html')

@app.route('/webhook_delete', methods=['GET','POST'])
def webhook_delete():

    webhook={}
    for key, value in request.form.items():
        webhook[key]=value
    
    print("webhook : ", webhook)
    
    headers = {
            "X-Shopify-Access-Token": session.get("access_token"),
            "Content-Type": "application/graphql",
            "Accept": "application/json",
        }
    
    url='https://{0}/admin/api/2020-04/graphql'.format(session['shop'])

    query='''
    mutation webhookSubscriptionDelete($id: ID!) {
        webhookSubscriptionDelete(id: $id) {
            deletedWebhookSubscriptionId
            userErrors {
                field
                message
            }
        }
    }
    '''

    variables={
        "id": webhook["id"],
    }

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query, variables)

    with open('delete_webhook.json','w') as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)
    
    with open('delete_webhook.json', 'r') as f:
        response = json.load(f)
        print(response)
        if response.get('data'):
            webhook_deleted=response["data"]["webhookSubscriptionDelete"]["deletedWebhookSubscriptionId"]
            return render_template("webhook_deleted.html")
        
        else:
            return render_template("error.html")

@app.route('/products', methods=['GET'])
def products():
    """ Get a stores products """
    """headers = {
        "X-Shopify-Access-Token": session.get("access_token"),
        "Content-Type": "application/json"
    }

    endpoint = "/admin/products.json"
    response = requests.get("https://{0}{1}".format(session.get("shop"),
                                                   endpoint), headers=headers)"""
    
    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }
    query ='''
        {
            products(first:5){
                edges{
                    node{
                        title
                        variants(first:1){
                            edges{
                                node{
                                    id
                                    priceV2{
                                        amount
                                    }
                                }   
                            }
                        }
                    }
                }
            }
        }'''

    endpoint = HTTPEndpoint(url,headers)
    data=endpoint(query)

    with open("query_products.json","w") as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)

    with open("query_products.json","r") as f:
        response = json.load(f)
        if response.get("data",False):
            nodes = response["data"]["products"]["edges"][:]
            if len(nodes)==0:
                return render_template('products.html', vide=True)
            else:
                products=[]
                for dic in nodes:
                    products.append({
                        "title": dic["node"]["title"],
                        "price": dic["node"]["variants"]["edges"][0]["node"]["priceV2"]["amount"],
                        "id": dic["node"]["variants"]["edges"][0]["node"]["id"],
                        })
                return render_template('products.html', products=products)
        else:
            return render_template("error.html")

@app.route('/product_page/<handle>', methods=['GET'])
def product_page(handle):

    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
        "X-Shopify-Storefront-access-token": session['storefront_access_token'],
        "Accept": "application/json",
        "Content-type": "application/graphql",
    }

    query='''
    query ($handle:String!){
        productByHandle(handle:$handle){
            images(first:1){
                edges{
                    node{
                        transformedSrc
                    }
                } 
            }
            variants(first:10){
                edges{
                    node{
                        title
                        id
                    }
                }
            }
            description
            title
            priceRange{
                maxVariantPrice{
                    amount
                }
            }
        }
    }
    '''

    variables={
        "handle":handle,
    }

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query,variables)

    print(data)
    resp=data.get("data")
    product=resp.get("productByHandle")
    if len(product["images"]["edges"])>0:
        image=product["images"]["edges"][0]["node"]["transformedSrc"]
    else:
        image=None
    variant=[]
    if len(product["variants"]["edges"])>1:
        for node in product["variants"]["edges"]:
            variant.append({
                "title":node["node"]["title"],
                "id":node["node"]["id"],
            })
    else:
        variant=None
    title=product["title"]
    price=product["priceRange"]["maxVariantPrice"]["amount"]
    description=product["description"]
    if len(description)==0:
        description=None

    finalData={
        "title":title,
        "variants":variant,
        "price":price,
        "image":image,
        "description":description,
    }
    return render_template('product_page.html', product=finalData)

@app.route('/cart', methods=['GET'])
def cart():

    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
        "X-Shopify-Storefront-access-token": session['storefront_access_token'],
        "Accept": "application/json",
        "Content-type": "application/graphql",
    }

    query='''
        query ($token:String!){
            customer(customerAccessToken:$token){
                lastIncompleteCheckout{
                    id
                    webUrl
                    totalPriceV2{
                        amount
                    }
                    lineItems(first:10){
                        edges{
                            node{
                                title
                                quantity
                                variant{
                                    id
                                    priceV2{
                                        amount
                                    }
                                }                            
                            }
                        }
                    }
                }
            }
        }
    '''
    variables={
        'token': session["customerAccessToken"],
    }

    endpoint=HTTPEndpoint(url,headers)
    data=endpoint(query,variables)

    with open('open_cart.json','w') as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)

    with open('open_cart.json','r') as f:
        resp=json.load(f)
        print("resp : ", resp)
        if resp["data"]["customer"]["lastIncompleteCheckout"]== None:
            create_cart(session["customerAccessToken"])
            print("a cart is created")
            return render_template('cart.html', vide=True)
        else:
            checkout_id=resp["data"]["customer"]["lastIncompleteCheckout"]["id"]
            price=resp["data"]["customer"]["lastIncompleteCheckout"]["totalPriceV2"]["amount"]
            url=resp["data"]["customer"]["lastIncompleteCheckout"]["webUrl"]
            items=resp["data"]["customer"]["lastIncompleteCheckout"]["lineItems"]["edges"][:]
            if len(items)==0:
                return render_template('cart.html', vide=True)
            else:
                products=[]
                for dic in items:
                        products.append({
                            "title": dic["node"]["title"],
                            "price": dic["node"]["variant"]["priceV2"]["amount"],
                            "quantity": dic["node"]["quantity"],
                            "id": dic["node"]["variant"]["id"],
                            })
            return render_template('cart.html', checkout=checkout_id, cart=products, total=price, url=url)

@app.route('/add_to_cart', methods=['GET','POST'])
def add_to_cart(): 
    """
    add a product to cart
    """

    product={}
    product_added=False

    for key, value in request.form.items():
        product[key]=value
    
    url='https://{0}/api/2020-04/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }

    query_checkout_id ='''
        query ($token:String!){
            customer(customerAccessToken:$token){
                lastIncompleteCheckout{
                    id
                    lineItems(first:10){
                        edges{
                            node{
                                title
                                quantity
                                variant{
                                    id
                                }
                            }
                        }
                    }
                }
            }
        }
    '''

    query_add ='''
        mutation checkoutLineItemsReplace($lineItems: [CheckoutLineItemInput!]!, $checkoutId: ID!) {
            checkoutLineItemsReplace(lineItems: $lineItems, checkoutId: $checkoutId) {
                checkout {
                    id
                    totalPriceV2{
                        amount
                    }
                    webUrl
                    lineItems(first:10){
                        edges{
                            node{
                                title
                                quantity
                                variant{
                                    priceV2{
                                        amount
                                    }
                                }
                            }
                        }
                    }
                }
                userErrors {
                    code
                    field
                    message
                }
            }
        }
        '''
    
    variables_checkout_id={
        "token":session["customerAccessToken"],
    }

    endpoint = HTTPEndpoint(url,headers)
    data=endpoint(query_checkout_id, variables_checkout_id)

    with open("checkout.json",'w') as f:
        json.dump(data,f, sort_keys=True, indent=2, default=str)
    
    with open("checkout.json",'r') as f:
        response = json.load(f)
        checkout=response["data"]["customer"]["lastIncompleteCheckout"]
        checkout_id=checkout["id"]
        line_items_nodes=checkout["lineItems"]["edges"][:]

        variables_add={
            "lineItems": [],
            "checkoutId": checkout_id,
        }

        for item in line_items_nodes:
            if item["node"]["variant"]["id"]!=product["productId"]:
                variables_add["lineItems"].append({
                    "quantity":int(item["node"]["quantity"]),
                    "variantId": item["node"]["variant"]["id"],
                })
            else:
                variables_add["lineItems"].append({
                    "quantity":int(product["quantity"])+int(item["node"]["quantity"]),
                    "variantId": product["productId"],
                })

                product_added=True
            
        if not(product_added):
            variables_add["lineItems"].append({
                "quantity":int(product["quantity"]),
                "variantId": product["productId"],    
            })

        endpoint_add=HTTPEndpoint(url,headers)
        data_add=endpoint_add(query_add,variables_add)

        with open('add_to_cart.json','w') as f2:
            json.dump(data_add,f2, sort_keys=True, indent=2, default=str)

        with open('add_to_cart.json') as f2:
            response_add=json.load(f2)
            checkout_updated=response_add["data"]["checkoutLineItemsReplace"]["checkout"]
            items = checkout_updated["lineItems"]["edges"][:]
            products=[]
            for dic in items:
                products.append({
                    "title": dic["node"]["title"],
                    "price": dic["node"]["variant"]["priceV2"]["amount"],
                    "quantity": dic["node"]["quantity"],
                    })
            return render_template("cart.html", checkout=checkout_id, cart=products, total=checkout_updated["totalPriceV2"]["amount"], url=checkout_updated["webUrl"])

@app.route('/update_cart', methods=['GET','POST'])
def update_cart():
    products={}
    info={}
    for key, value in request.form.items():
        if key == "checkout":
            checkout_id=value
        else:
            key=key.split("_")[0]
            info[key]=value
            if key == "quantity":
                products[info["title"]]=dict(info)
                info={}

    url='https://{0}/api/2020-04/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }
    
    query_update ='''
        mutation checkoutLineItemsReplace($lineItems: [CheckoutLineItemInput!]!, $checkoutId: ID!) {
            checkoutLineItemsReplace(lineItems: $lineItems, checkoutId: $checkoutId) {
                checkout {
                    id
                    totalPriceV2{
                        amount
                    }
                    webUrl
                    lineItems(first:10){
                        edges{
                            node{
                                title
                                quantity
                                variant{
                                    priceV2{
                                        amount
                                    }
                                }
                            }
                        }
                    }
                }
                userErrors {
                    code
                    field
                    message
                }
            }
        }
        '''

    variable={
        "lineItems":[],
        "checkoutId":checkout_id
    }

    for key,value in products.items():
        variable["lineItems"].append({
            "quantity": int(products[key]["quantity"]),
            "variantId": products[key]["productId"],
        })
    
    endpoint=HTTPEndpoint(url,headers)
    endpoint(query_update, variable)

    return render_template("cart_updated.html")
    
@app.route('/signup', methods=['GET'])
def signup():
    """
    Create a new customer
    """
    return render_template('signup.html')

@app.route('/signup_form', methods=['GET','POST']) #a finir il reste l'erreur a gerer
def need_input_signup():
    """
    Retreiving values from the signup form
    """
    dic={}

    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        dic[key]=value
    
    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }
    query ='''
        mutation customerCreate($input: CustomerCreateInput!) {
            customerCreate(input: $input) {
                customer {
                    id
                    firstName
                    lastName
                    lastIncompleteCheckout{
                        id
                    }
                }
                customerUserErrors {
                code
                field
                message
                }
            }
            }
        '''
    query_acess_token='''
        mutation customerAccessTokenCreate($input: CustomerAccessTokenCreateInput!) {
            customerAccessTokenCreate(input: $input) {
                customerAccessToken {
                    accessToken
                    expiresAt
                }
                customerUserErrors {
                    code
                    field
                    message
                }
            }
        }
    '''
    variables_access_token = {
        "input":{
        'email': dic['email'],
        'password': dic['pwd']
        }
    }

    variables = {
        "input":{
        'firstName': dic['fname'],
        'lastName': dic['lname'],
        'email': dic['email'],
        'password': dic['pwd']
        }
    }

    endpoint = HTTPEndpoint(url,headers)
    data=endpoint(query, variables)

    with open("create_customer.json","w") as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)

    with open("create_customer.json","r") as f:
        response = json.load(f)
        print(response)
        if response.get("errors",False):
            errors=response["errors"][:]
            messages=[]
            for error in errors:
                messages.append(error["message"])
            return render_template('signup.html',error=messages)

        elif response["data"]["customerCreate"].get("customer",False):

            endpoint_access_token = HTTPEndpoint(url,headers)
            data_access_token=endpoint_access_token(query_acess_token,variables_access_token)

            with open("log_customer.json","w") as f2:
                json.dump(data_access_token, f2, sort_keys=True, indent=2, default=str)

            with open("log_customer.json","r") as f2:
                response_access_token = json.load(f2)
                token = response_access_token['data']['customerAccessTokenCreate']["customerAccessToken"]
                session['customerAccessToken']=token['accessToken']

            customer = response['data']['customerCreate']['customer']
            customer['access_token']=token['accessToken']

        elif response["data"]["customerCreate"].get('customerUserErrors',False):
            errors=response.get("data").get("customerCreate").get("customerUserErrors")[:]
            print(errors)
            messages=[]
            for error in errors:
                messages.append(error["message"])
            return render_template('signup.html', fname=dic['fname'], lname=dic['lname'], email=dic["email"], error=messages)


    return render_template('signed.html', customer=customer)

@app.route('/login', methods=['GET'])
def login():
    """
    simulate a login by creating a customer access token
    """
    return render_template('login.html')

@app.route('/login_form', methods=['GET','POST'])#a finir il reste l'erreur a gerer
def need_input_login():

    login_info={}

    for key, value in request.form.items():
        login_info[key]=value

    url='https://{0}/api/2019-07/graphql'.format(session['shop'])
    headers={
            "X-Shopify-Storefront-access-token": session['storefront_access_token'],
            "Accept": "application/json",
            "Content-type": "application/graphql",
        }
    query ='''
        mutation customerAccessTokenCreate($input: CustomerAccessTokenCreateInput!) {
            customerAccessTokenCreate(input: $input) {
                customerAccessToken {
                    accessToken
                    expiresAt
                }
                customerUserErrors {
                    code
                    field
                    message
                }
            }
            }
        '''
    query_name='''
        query ($token: String!){
            customer(customerAccessToken: $token){
                firstName
                lastName
            }
        }
    '''

    variables = {
        "input":{
        'email': login_info['email'],
        'password': login_info['pwd']
        }
    }

    endpoint = HTTPEndpoint(url,headers)
    data=endpoint(query, variables)

    with open("log_customer.json","w") as f:
        json.dump(data, f, sort_keys=True, indent=2, default=str)

    with open("log_customer.json","r") as f:
        response = json.load(f)
        print(response)
        if response['data']['customerAccessTokenCreate'] != 'null':
            token = response['data']['customerAccessTokenCreate']["customerAccessToken"]
            session['customerAccessToken']=token['accessToken']

            variable_name={
                "token":token['accessToken']
            }

            data_name=endpoint(query_name,variable_name)
            response_name=data_name
            print(response_name)

            fname=response_name["data"]["customer"]["firstName"]
            lname=response_name["data"]["customer"]["lastName"]

            session["fname"]=fname
            session["lname"]=lname

            return render_template('logged.html', token=token)

@app.route('/log_out', methods=['GET'])
def log_out():
    if session.get("customerAccessToken"):
        del session['customerAccessToken']
        del session['fname']
        del session['lname']

        return render_template("logged_out.html")
    else :
        return render_template('error.html')

@app.route('/install', methods=['GET'])
def install():
    """
    Connect a shopify store
    """
    if request.args.get('shop'):
        shop = request.args.get('shop')
    else:
        return Response(response="Error:parameter shop not found", status=500)

    auth_url = "https://{0}/admin/oauth/authorize?client_id={1}&scope={2}&redirect_uri={3}".format(
        shop, cfg.SHOPIFY_CONFIG["API_KEY"], cfg.SHOPIFY_CONFIG["SCOPE"],
        cfg.SHOPIFY_CONFIG["REDIRECT_URI"]
    )
    print("Debug - auth URL: ", auth_url)
    return redirect(auth_url)

@app.route('/connect', methods=['GET'])
def connect():
    if request.args.get("shop"):
        params = {
            "client_id": cfg.SHOPIFY_CONFIG["API_KEY"],
            "client_secret": cfg.SHOPIFY_CONFIG["API_SECRET"],
            "code": request.args.get("code")
        }
        resp = requests.post(
            "https://{0}/admin/oauth/access_token".format(
                request.args.get("shop")                
            ),
            data=params
        )

        if 200 == resp.status_code:
            resp_json = json.loads(resp.text)
            session['access_token'] = resp_json.get("access_token")
            session['scopes'] = resp_json.get("scope")
            session['shop'] = request.args.get("shop")

            token=get_storefront_access_tokens()
            print("token : ",token)
            if len(token)==0:
                session["storefront_access_token"]=create_storefront_token()
            elif len(token)>=2:
                token=delete_token(token)
                session["storefront_access_token"]=token["token"]
            else:
                session["storefront_access_token"]=token[0]["token"]

            dic={
                "storefront": session["storefront_access_token"],
                "admin": session["access_token"]
            }
            return render_template('welcome.html', from_shopify=dic, fname=session.get("fname"), lname=session.get('lname'))
        else:
            print("Failed to get access token: ", resp.status_code, resp.text)
            return render_template('error.html')

@app.route('/home', methods=['GET'])
def home():
    dic={
        "storefront": session["storefront_access_token"],
        "admin": session["access_token"]
    }
    return render_template('welcome.html', fname=session.get("fname"), lname=session.get('lname'), from_shopify=dic)

@app.route('/session', methods=['GET'])
def get_session():
    print(session)
    return "200"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1337)