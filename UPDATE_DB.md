# Updating the production database

The database is only read from, never written to, so you can create it locally and then upload the entire database onto the database server. When all of the heavy computing is done locally, we don't have to pay for a powerful backend server. In order to eliminate downtime, follow this process:

* Create new database on the database server (for example, using pgAdmin)
* Upload contents onto the new database
    * pg_dump `db_name` > `file_name` --format custom
    * pg_restore -h nettipuoskari-prod.crqdrenwhmiv.eu-central-1.rds.amazonaws.com -p 5432 -d `db_name` -U master `file_name`
    * insert password
    * wait (shouldn't take more than a few hours)
* Update access rights using psql:
    * Run `psql --host=<host> --port=5432 --username=master --dbname=laaketutka < scripts/grant_access.sql`
* Alternatively, using pgAdmin:
    * Click on databases
    * Click on `db_name`
    * Right-click on public
    * Click on grant wizard
    * Tab selection: choose all
    * Tab privileges: choose nettipuoskari_read_only
* Configure backend to use the new database
* Test that everything works
* Remove the old database if necessary