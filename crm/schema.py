import graphene
from graphene_django import DjangoObjectType
from .models import Customer, Product, Order
import re
from django.db import transaction
from django.utils import timezone
import django_filters
from graphene_django.filter import DjangoFilterConnectionField
from crm.models import Product 

# Define ProductType for GraphQL
class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "stock")


# Mutation class
class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no arguments, just updates all low stock

    updated_products = graphene.List(ProductType)
    message = graphene.String()

    def mutate(self, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated = []

        for product in low_stock_products:
            product.stock += 10
            product.save()
            updated.append(product)

        return UpdateLowStockProducts(
            updated_products=updated,
            message=f"{len(updated)} products updated successfully!",
        )


# Root mutation
class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()


# Schema entry point
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello World!")  # useful for Task 2
    # add your other queries here...

schema = graphene.Schema(query=Query, mutation=Mutation)



# === GraphQL Types ===
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone", "created_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone']


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['name', 'price']


class OrderFilter(django_filters.FilterSet):
    customer_name = django_filters.CharFilter(field_name='customer__name', lookup_expr='icontains')
    min_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    start_date = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')

    class Meta:
        model = Order
        fields = ['customer_name', 'min_total', 'max_total', 'start_date', 'end_date']

class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType, filterset_class=CustomerFilter)
    all_products = DjangoFilterConnectionField(ProductType, filterset_class=ProductFilter)
    all_orders = DjangoFilterConnectionField(OrderType, filterset_class=OrderFilter)


    def resolve_all_customers(root, info):
        return Customer.objects.all()

    def resolve_all_products(root, info):
        return Product.objects.all()

    def resolve_all_orders(root, info):
        return Order.objects.select_related("customer").prefetch_related("products").all()

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

# === CreateCustomer Mutation ===
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(lambda: CustomerType)
    message = graphene.String()

    def mutate(root, info, input):
        # Email uniqueness check
        if Customer.objects.filter(email=input.email).exists():
            raise Exception("Email already exists.")

        # Optional phone validation
        if input.phone:
            phone_pattern = re.compile(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$')
            if not phone_pattern.match(input.phone):
                raise Exception("Invalid phone format.")

        customer = Customer(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        customer.save()

        return CreateCustomer(customer=customer, message="Customer created successfully.")
    
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)

    customers = graphene.List(lambda: CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(root, info, inputs):
        created_customers = []
        errors = []

        # Start a transaction for bulk creation
        with transaction.atomic():
            for idx, input in enumerate(inputs):
                try:
                    # Email uniqueness
                    if Customer.objects.filter(email=input.email).exists():
                        raise Exception(f"Email already exists: {input.email}")

                    # Optional phone validation
                    if input.phone:
                        phone_pattern = re.compile(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$')
                        if not phone_pattern.match(input.phone):
                            raise Exception(f"Invalid phone format: {input.phone}")

                    customer = Customer(
                        name=input.name,
                        email=input.email,
                        phone=input.phone
                    )
                    customer.save()
                    created_customers.append(customer)

                except Exception as e:
                    errors.append(f"Record {idx + 1}: {str(e)}")
                    # Do not stop the loop — allow other valid records

        return BulkCreateCustomers(customers=created_customers, errors=errors)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(lambda: ProductType)
    message = graphene.String()

    def mutate(root, info, input):
        # Validation
        if input.price <= 0:
            raise Exception("Price must be positive.")
        if input.stock < 0:
            raise Exception("Stock cannot be negative.")

        product = Product(
            name=input.name,
            price=input.price,
            stock=input.stock
        )
        product.save()

        return CreateProduct(product=product, message="Product created successfully.")

class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)  # optional


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(lambda: OrderType)
    message = graphene.String()

    def mutate(root, info, input):
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=input.customer_id)
        except Customer.DoesNotExist:
            raise Exception(f"Customer ID {input.customer_id} does not exist.")

        # Validate product IDs
        products = Product.objects.filter(id__in=input.product_ids)
        if not products.exists():
            raise Exception("No valid products provided.")
        if len(products) != len(input.product_ids):
            invalid_ids = set(input.product_ids) - set(str(p.id) for p in products)
            raise Exception(f"Invalid product IDs: {', '.join(invalid_ids)}")

        # Set order_date or default to now
        order_date = input.order_date or timezone.now()

        # Calculate total_amount
        total_amount = sum(p.price for p in products)

        # Create Order
        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=order_date
        )
        order.products.set(products)

        return CreateOrder(order=order, message="Order created successfully.")




class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()