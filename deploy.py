from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import transaction
from algosdk import logic
import base64

# Testnet configuration
ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""
ALGOD_HEADERS = {"X-API-Key": ""}

def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

def create_app(client, private_key, approval_program, clear_program, global_schema, local_schema):
    sender = account.address_from_private_key(private_key)
    
    params = client.suggested_params()
    
    # Create application
    txn = transaction.ApplicationCreateTxn(
        sender=sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
        extra_pages=1
    )
    
    # Signing and sending the tx
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()
    
    client.send_transaction(signed_txn)
    
    # Wait for confirmation
    transaction.wait_for_confirmation(client, tx_id, 4)
    
    # Getting application ID
    response = client.pending_transaction_info(tx_id)
    app_id = response['application-index']
    
    print(f'Created app with id: {app_id}')
    return app_id

def call_deposit(client, private_key, app_id, github_handle, deposit_amount=1000000):
    sender = account.address_from_private_key(private_key)
    app_addr = logic.get_application_address(app_id)
    
    params = client.suggested_params()
    
    # Payment transaction for deposit
    payment_txn = transaction.PaymentTxn(
        sender=sender,
        sp=params,
        receiver=app_addr,
        amt=deposit_amount
    )
    
    # App call transaction of github handle
    app_args = [
        bytes("deposit", "utf-8"),
        bytes(github_handle, "utf-8")
    ]
    
    app_txn = transaction.ApplicationCallTxn(
        sender=sender,
        sp=params,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=app_args,
        boxes=[(app_id, bytes("github", "utf-8"))]
    )
    
    # Group transactions
    gid = transaction.calculate_group_id([payment_txn, app_txn])
    payment_txn.group = gid
    app_txn.group = gid
    
    # Sign transactions
    signed_payment = payment_txn.sign(private_key)
    signed_app = app_txn.sign(private_key)
    
    # Send group
    client.send_transactions([signed_payment, signed_app])
    
    # Wait for confirmation
    tx_id = signed_app.transaction.get_txid()
    transaction.wait_for_confirmation(client, tx_id, 4)
    
    print(f'Deposit called successfully with github handle: {github_handle}')
    return tx_id

def main():
    # Initializing the algod client
    algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    # Geting the algorand blockchain account from mnemonic
    MNEMONIC = "25-words-mnemonic"
    private_key = mnemonic.to_private_key(MNEMONIC)
    sender = account.address_from_private_key(private_key)
    
    print(f"Using account: {sender}")
    
    # Check balance
    account_info = algod_client.account_info(sender)
    print(f"Account balance: {account_info.get('amount')} microAlgos")
    
    # Compile programs
    print("Compiling programs...")
    with open("approval.teal", "r") as f:
        approval_source = f.read()
    with open("clear.teal", "r") as f:
        clear_source = f.read()
    
    approval_program = compile_program(algod_client, approval_source)
    clear_program = compile_program(algod_client, clear_source)
    
    # Defining the schema
    global_schema = transaction.StateSchema(num_uints=1, num_byte_slices=1)
    local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)
    
    # Creating application
    print("Deploying application...")
    app_id = create_app(algod_client, private_key, approval_program, clear_program, global_schema, local_schema)
    
    # Call deposit method with github handle
    github_handle = "@princemishraji"  # Replace with your GitHub handle
    print(f"Calling deposit method with github handle: {github_handle}")
    tx_id = call_deposit(algod_client, private_key, app_id, github_handle)
    
    # Verify box creation
    print("Verifying box storage...")
    try:
        box_info = algod_client.application_box_by_name(app_id, bytes("github", "utf-8"))
        print(f"Box created successfully!")
        print(f"Box name: {base64.b64decode(box_info['name'])}")
        print(f"Box value: {base64.b64decode(box_info['value'])}")
    except Exception as e:
        print(f"Error reading box: {e}")
    
    print(f"\n{'='*50}")
    print(f"DEPLOYMENT COMPLETE!")
    print(f"Application ID: {app_id}")
    print(f"GitHub handle stored: {github_handle}")
    print(f"{'='*50}")
    
    return app_id

if __name__ == "__main__":
    app_id = main()