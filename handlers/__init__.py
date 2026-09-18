def register_handlers(app):

    from telegram.ext import CommandHandler
    from .start import start

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )