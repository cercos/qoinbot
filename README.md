# ![alt text](qoinbot.png "Qoinbot") Qoinbot
A cryptocurrency super bot with paper trading

Need help? Visit the server: https://discord.gg/QH2vSmU

## Requirements
- Python 3.6 and up - https://www.python.org/downloads/
- git - https://git-scm.com/download/

## Optional tools
- Flake8 - Python Module (Keeps your code clean)
  - If you're using python 3.7, install by doing
  ```
  pip install -e git+https://gitlab.com/pycqa/flake8#egg=flake8
  ```
- PM2 - NodeJS Module (Keeps the bot alive)
  - Requires NodeJS - https://nodejs.org/en/download/


## Usage
The command prefix by default is "?" and will be used below, be sure to use the correct prefix if the server has a custom prefix set.  All commands can be viewed using the bot with the "?help" command.

Commands a long and short hand form both will be shown below.

<> - denote a required argument

[] - denote an optional argument
## Economy
##### Check your balance
```
?balance
?bal
```
##### Collect your wage
```
?wage
```
##### Collect Qoins generated from items
```
?collect
?c
```
##### Check your item inventory
```
?inventory
?inv
```
##### Deposit to bank
```
?deposit <amount>
?dep <amount>
```
##### Withdrawal to pocket
```
?withdrawal <amount>
?with <amount>
```
##### Set quote command
*This command sets the quote you will see all prices in including any Qoin values*
```
?setquote <symbol>
?sq <symbol>
```
## Price checking
### Price command
```
?price <coin symbol>
?p <coin_symbols>
```
### Price list commands
The price list command saves a list of symbols so you don't have to type them out every time.
##### Check the price list
```
?pricelist
?pl
```
##### Add a symbol to the price list
```
?pricelist add <coin_symbols>
?pl a <coin_symbols>
```
##### Delete a symbol from the price list
```
?pricelist delete <coin_symbols>
?pl d <coin_symbols>
```
##### Clear all symbols from the price list
```
?pricelist clear | nuke 
```
## Game and Store
### How the game works
The game starts each player with 250 Qoins, the bot's native currency which represent USD value by default. Each player has a starting wage of 25 Qoins per hour and can be collected at least 1 hour a players last collection and can accumulate for 100 hours max.  Players can paper trade using the Qoins and build up their networth.  Items can also be purchased in the store which will either increase a players wage or certain items like miners can be purchased for side income.  The goal is simply to have the highest networth.  
### Portfolio commands
##### View your portfolio
```
?portfolio [page=1]
?po [page=1]
```
##### View another users portfolio
```
?portfolio user <user> [page=1]
?po u <user> [page=1]
```
##### View a portfolio holding
```
?portfolio holding <coin_symbol>
?po h <coin_symbol>
```
### Store commands
##### View a list of available stores
```
?view
?v
```
##### View a store
```
?view <store_name>
?v <store_name>
```
### Buy/Sell commands
*When buying crypto the amount in a command is in reference to Qoins, when selling the amount is reference to the crypto*
##### Buy an item from the store
```
?buy <item_name>
?b <item_name>
```
##### Sell an item from the store
```
?sell <item_name>
?s <item_name>
```
##### Buy a coin for your portfolio
```
?buy coin <amount> <coin_symbol>
?b c <amount> <coin_symbol>
```
##### Sell a coin from your portfolio
```
?sell coin <amount> <coin_symbol>
?s c <amount> <coin_symbol>
```
