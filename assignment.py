from pyteal import *

def approval_program():
    handle_creation = Seq([
        App.globalPut(Bytes("owner"), Txn.sender()),
        Approve()
    ])

    # Method selector
    deposit_method = Bytes("deposit")

    # Box operation
    github_box_key = Bytes("github")

    handle_var = ScratchVar(TealType.bytes)
    # Deposit method with github handle storage
    deposit = Seq([
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),


        handle_var.store(Txn.application_args[1]),

        App.box_put(github_box_key, handle_var.load()),

        # Logging for verification of username
        Log(Concat(Bytes("GitHub handle stored: "), handle_var.load())),

        Approve()
    ])


    # Router logic
    handle_noop = Cond(
        [Txn.application_args[0] == deposit_method, deposit]
    )

    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.UpdateApplication, Reject()],
        [Txn.on_completion() == OnComplete.DeleteApplication, Reject()],
    )

    return program

def clear_state_program():
    return Approve()

if __name__ == "__main__":
    # Compile contracts
    with open("approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=8)
        f.write(compiled)
    
    with open("clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=8)
        f.write(compiled)
    
    print("Contracts compiled successfully!")
    print("Approval program saved to: approval.teal")
    print("Clear state program saved to: clear.teal")