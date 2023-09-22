import sqlite3
from PyQt6.QtWidgets import QMainWindow, QTableWidgetItem, QTableWidget
from PyQt6.QtCore import Qt
from sqlite3.dbapi2 import connect
from DataBuilder import DataBuilder

from Window_UI import Ui_MainWindow

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('FIInfo')
        self.database = 'database.db'
        self.dataBuilder = DataBuilder()
        
        self.ui.addFiiPushButton.clicked.connect(self.addFiiToTable)
        self.ui.removeFiiPushButton.clicked.connect(self.removeFiiFromTable)
        
        connection = self.createDbConnection()
        self.updateTable(connection)
        connection.close()
    
    def updateTable(self, connection):
        sql = 'SELECT * FROM fiis'
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        rowsLength = len(rows)
        if rows:
            columnsLength = len(rows[0])
        else:
            columnsLength = 0
        self.ui.fiiTableWidget.setRowCount(rowsLength)
        self.ui.fiiTableWidget.setColumnCount(columnsLength)
        headerLabels = ['grupo', 'ticker', 'valor atual (R$)', 'yield 12M (%)', 'P/VP', 
                        'yield 12M projetado (%)', 'premio (%)', 'preco teto (R$)', 
                        'preco teto projetado (R$)', 'preco teto / valor atual',
                        'preco teto projetado / valor atual']
        self.ui.fiiTableWidget.setHorizontalHeaderLabels(headerLabels)
        
        for i in range(rowsLength):
            for j in range(columnsLength):
                item = QTableWidgetItem(f"{rows[i][j]}")
                self.ui.fiiTableWidget.setItem(i,j, item)
    
    def createDbConnection(self):
        return connect(self.database)
    
    def operateTable(self, sql, sql_array):
        connection = self.createDbConnection()
        cursor = connection.cursor()
        cursor.execute(sql, sql_array)
        connection.commit()
        cursor.close()
        self.updateTable(connection)
        connection.close()
    
    def insertToTable(self, ticker, premio, grupo):
        sql = '''INSERT INTO fiis(ticker, premio, valor_atual, grupo)
                 VALUES (?, ?, ?, ?)'''
        if self.ui.fiiTableWidget.findItems(ticker, Qt.MatchFlag.MatchContains):
            return
        else:
            valor_atual = self.dataBuilder.getPrice(ticker)
            self.operateTable(sql, [ticker, float(premio), valor_atual, grupo])
        
    def deleteFromTable(self, ticker):
        sql = 'DELETE FROM fiis WHERE ticker = ?'
        self.operateTable(sql, [ticker])
        
    def addFiiToTable(self):
        ticker = self.ui.tickerLineEdit.text()
        premio = self.ui.premioLineEdit.text()
        grupo = self.ui.grupoLineEdit.text()
        if ticker and premio and grupo:
            self.insertToTable(ticker, premio, grupo)
        else:
            return
            
    def removeFiiFromTable(self):
        currentRow = self.ui.fiiTableWidget.currentRow()
        tickerRowIndex = self.ui.fiiTableWidget.model().index(currentRow, 0)
        ticker = self.ui.fiiTableWidget.model().data(tickerRowIndex)
        if ticker:
            self.deleteFromTable(ticker)
        else:
            return