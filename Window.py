from PyQt6.QtWidgets import QMainWindow, QTableWidgetItem
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont
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
        self.ui.pushButton.clicked.connect(self.filterGroup)
        self.ui.actionyields_12M_projetado.triggered.connect(self.updateProjectedData)
        
        self.setLoading(True)
        self.ui.ntnbLineEdit.setText(str(self.dataBuilder.ntnbTax))
        self.ui.ipcaLineEdit.setText(str(self.dataBuilder.ipca))
        connection = self.createDbConnection()
        self.loadFilterGroups(connection)
        self.updateData(connection)
        connection.close()
        self.setLoading(False)
    
    def updateTable(self, connection, filter = ''):
        if filter:
            filter = f"WHERE grupo = '{filter}'"
        sql = f"SELECT * FROM fiis {filter} ORDER BY grupo, p_vp"
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        rowsLength = len(rows)
        columnsLength = 12 if rows else 0
        self.ui.fiiTableWidget.setRowCount(rowsLength)
        self.ui.fiiTableWidget.setColumnCount(columnsLength)
        headerLabels = ['grupo', 'ticker', 'valor atual\n(R$)', 'P/VP', 'premio (%)', 
                        '+ IPCA?', 'yield 12M\n(%)', 'yield 12M\nprojetado\n(R$)', 'preco teto\n(R$)', 
                        'preco teto\nprojetado\n(R$)', 'preco teto\n/\nvalor atual',
                        'preco teto\nprojetado /\nvalor atual']
        self.ui.fiiTableWidget.setHorizontalHeaderLabels(headerLabels)
        for i in range(rowsLength):
            valorAtual = rows[i][2]
            premio = rows[i][4]
            addIpcaToPremio = rows[i][5]
            yield12 = rows[i][6]
            rendimento12Projetado = rows[i][7]
            precoTeto, tetoValor = self.dataBuilder.calculateBaseData(yield12, premio, addIpcaToPremio, valorAtual)
            yield12Projected, precoTetoProjected, tetoProjetadoValor = self.dataBuilder.calculateProjectedData(rendimento12Projetado, premio, addIpcaToPremio, valorAtual)
            for j in range(columnsLength):
                if j == 5:
                   item = bool(addIpcaToPremio)
                elif j == 7:
                   item = yield12Projected
                elif j == 8:
                    item = precoTeto
                elif j == 9:
                    item = precoTetoProjected
                elif j == 10:
                    item = tetoValor
                elif j == 11:
                    item = tetoProjetadoValor
                else:
                    item = rows[i][j]
                widgetItem = QTableWidgetItem(f"{item}")
                flags = Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable
                if j == 4 or j == 5:
                    flags = flags|Qt.ItemFlag.ItemIsEditable
                widgetItem.setFlags(flags)
                widgetItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.fiiTableWidget.setItem(i,j, widgetItem)
    
    def createDbConnection(self):
        return connect(self.database)
    
    def operateTable(self, sql, sql_array, connection = False):
        initialConnection = connection
        if not connection:
            connection = self.createDbConnection()
        cursor = connection.cursor()
        cursor.execute(sql, sql_array)
        connection.commit()
        cursor.close()
        self.updateTable(connection)
        if not initialConnection:
            connection.close()
     
    def updateData(self, connection):
        cursor = connection.cursor()
        rows = self.ui.fiiTableWidget.rowCount()
        for i in range(rows):
            self.baseUpdateRow(i, cursor, connection)
        cursor.close()
        self.updateTable(connection)
    
    def baseUpdateRow(self, row, cursor, connection):
        sql = '''UPDATE fiis
                 SET valor_atual = ?, yield_12 = ?, p_vp = ?)
                 WHERE ticker = ?'''
        tickerRowIndex = self.ui.fiiTableWidget.model().index(row, 0)
        premioRowIndex = self.ui.fiiTableWidget.model().index(row, 6)
        ticker = self.ui.fiiTableWidget.model().data(tickerRowIndex)
        premio = self.ui.fiiTableWidget.model().data(premioRowIndex)
        valorAtual, yield12, pVp = self.dataBuilder.getBaseData(ticker, float(premio))
        cursor.execute(sql, [valorAtual, yield12, pVp])
        connection.commit()
    
    def insertToTable(self, ticker, premio, grupo, addIpcaToPremio):
        sql = '''INSERT INTO fiis(grupo, ticker, valor_atual, p_vp, premio, ipca_no_premio, yield_12, rendimento_12_projetado)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        if self.ui.fiiTableWidget.findItems(ticker, Qt.MatchFlag.MatchContains):
            return
        else:
            valorAtual, yield12, pVp = self.dataBuilder.getBaseData(ticker, float(premio))
            rendimento12Projected = self.dataBuilder.getNext12MProjectedIncome(ticker)
            self.operateTable(sql, [grupo, ticker, valorAtual, pVp, float(premio), addIpcaToPremio, yield12, rendimento12Projected])
            position = self.ui.comboBox.count()
            self.addGroupToComboBox(grupo, position)
        
    def deleteFromTable(self, ticker):
        sql = 'DELETE FROM fiis WHERE ticker = ?'
        connection = self.createDbConnection()
        self.operateTable(sql, [ticker], connection)
        self.loadFilterGroups(connection)
        connection.close()
        
    def addFiiToTable(self):
        self.setLoading(True)
        errorMessage = ''
        try:
            ticker = self.ui.tickerLineEdit.text()
            premio = self.ui.premioLineEdit.text()
            grupo = self.ui.grupoLineEdit.text()
            addIpcaToPremio = self.ui.addIpcaCheckBox.isChecked()
            if ticker and premio and grupo:
                self.insertToTable(ticker, premio, grupo, addIpcaToPremio)
        except:
            errorMessage = 'ERRO! Por favor, verifique o ticker'
        self.setLoading(False, errorMessage)
        
            
    def removeFiiFromTable(self):
        self.setLoading(True)
        currentRow = self.ui.fiiTableWidget.currentRow()
        itemRowIndex = self.ui.fiiTableWidget.model().index(currentRow, 1)
        ticker = self.ui.fiiTableWidget.model().data(itemRowIndex)
        if ticker:
            self.deleteFromTable(ticker)
        self.setLoading(False)
    
    def filterGroup(self):
        self.setLoading(True)
        connection = self.createDbConnection()
        filter = self.ui.comboBox.currentText()
        if filter == 'Todos':
            filter = ''
        self.updateTable(connection, filter)
        connection.close()
        self.setLoading(False)
        
    def addGroupToComboBox(self, group, position):
        groupExists = self.ui.comboBox.findText(group)
        if groupExists == -1:
            _translate = QCoreApplication.translate
            font = QFont()
            font.setPointSize(12)
            self.ui.comboBox.setFont(font)
            self.ui.comboBox.setObjectName("comboBox")
            self.ui.comboBox.addItem("")
            self.ui.comboBox.setItemText(position, _translate("MainWindow", group))
    
    def loadFilterGroups(self, connection):
        sql = 'SELECT DISTINCT grupo FROM fiis'
        cursor = connection.cursor()
        cursor.execute(sql)
        groups = cursor.fetchall()
        i = 1
        while i < self.ui.comboBox.count():
            self.ui.comboBox.removeItem(i)
        i = 1
        for group in groups:
            group = str(group).split("'")[1]
            self.addGroupToComboBox(group, i)
            i+= 1
            
    def updateProjectedData(self):
        self.setLoading(True)
        errorMessage = ''
        try:
            sql = "SELECT ticker FROM fiis"
            connection = self.createDbConnection()
            cursor = connection.cursor()
            cursor.execute(sql)
            tickers = cursor.fetchall()
            for ticker in tickers:
                sql = "UPDATE fiis SET rendimento_12_projetado = ? WHERE ticker = ?"
                ticker = str(ticker).split("'")[1]
                rendimento12Projected = self.dataBuilder.getNext12MProjectedIncome(ticker)
                self.operateTable(sql, [rendimento12Projected, ticker], connection)
            connection.close()
        except:
            errorMessage = 'ERRO! Tente novamente mais tarde'
        self.setLoading(False, errorMessage)
        
    def enableDisableAll(self, boolean):
        self.ui.centralwidget.setDisabled(boolean)
        self.ui.menubar.setDisabled(boolean)
        
    def setLoading(self, boolean, errorMessage = ''):
        if boolean:
            self.ui.statusbar.showMessage('Carregando...')
            self.enableDisableAll(True)
            QCoreApplication.processEvents()
        else:
            self.ui.statusbar.showMessage(errorMessage, 5000)
            self.enableDisableAll(False)