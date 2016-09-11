import rethinkdb as r
import os


class Database():
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.db_name = 'turbo'
        r.set_loop_type("asyncio")
        self.connected = False

    def get_db(self):
        """
        Returns the RethinkDB module/instance
        """
        return r

    async def insert(self, table, data):
        """
        Insert a document into a table
        """
        self.log.debug("Saving document to table {} with data: {}".format(table, data))
        return await r.table(table).insert(data, conflict="update").run(self.db)

    async def delete(self, table, primary_key=None):
        """
        Deletes a document(s) from a table
        """
        self.log.debug("Deleting document from table {} with primary key {}".format(table, primary_key))
        if primary_key is not None:
            # Delete one document with the key name
            return await r.table(table).get(primary_key).delete().run(self.db)
        else:
            # Delete all documents in the table
            return await r.table(table).delete().run(self.db)

    async def connect(self):
        """
        Establish a database connection
        """
        self.log.info("- Connecting to database...")
        try:
            self.db = await r.connect(db=self.db_name)
        except r.errors.ReqlDriverError as e:
            self.log.critical("Failed to connect")
            self.log.error(e)
            os._exit(1)
        info = await self.db.server()
        self.log.info("- Established connection. Server: {}".format(info['name']))

        # Create the database if it does not exist
        try:
            await r.db_create(self.db_name).run(self.db)
            self.log.info("- Created database: {}".format(self.db_name))
        except r.errors.ReqlOpFailedError:
            self.log.debug("Database {} already exists, skipping creation".format(self.db_name))

    async def create_table(self, name, primary='id'):
        """
        Creates a new table in the database
        """
        try:
            await r.table_create(name, primary_key=primary).run(self.db)
            self.log.info("- Created table: {}".format(name))
        except r.errors.ReqlOpFailedError:
            self.log.debug("Table {} already exists, skipping creation".format(name))
