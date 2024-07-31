import backtrader as bt
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

class SMA(bt.Strategy):
    params = (
        ('velas', 10), # default en 10, pero se ajusta en la definición de la estrategia
        ('data', None),# recuperamos la data para saber con qué activo debe operar esta estrategia
        ('operaciones', None),
    )

    def __init__(self):
        self.data1 = self.params.data # asignamos el activo con el que debe operar la instancia de la estrategia
        self.sma = bt.indicators.SimpleMovingAverage(self.data1, period=self.params.velas)
        self.size = 0
        self.position_active = False # se utiliza para no sobre comprar múltiples veces el mismo activo
        self.order = None
        
    def next(self):
        if self.order:
            return
        
        if self.data1.close[0] > self.sma[0] and not self.position_active:
            # obtenemos el equivalente en acciones que se pueden comprar con el 10% del total de la cartera
            self.size = int((self.broker.getvalue() * 0.10) / self.data1.close[0])
            # verificamos que el dinero disponible sea suficiente para comprar
            if self.broker.get_cash() > self.size * self.data1.close[0]:
                self.order = self.buy(data=self.data1, size=self.size)
            else:
                print('El dinero en la cuenta no es suficiente como para efectuar la compra')
        elif self.data1.close[0] < self.sma[0] and self.position_active:
            self.order = self.sell(data=self.data1, size=self.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.position_active = True
                self.log('compra', self.data1._name, order.executed.price)
            elif order.issell():
                self.position_active = False
                self.log('venta', self.data1._name, order.executed.price)
            self.order = None

    # registramos la operación en la lista
    def log(self, tipo, simbolo, Valor):
        saldo_total = self.broker.getvalue()
        dt = self.data1.datetime.date(0).isoformat()
        self.params.operaciones.append([dt, tipo, f'SMA {self.params.velas}', simbolo, Valor, self.size, (self.size * Valor), self.broker.get_cash(), saldo_total])

class CruceSMA(bt.Strategy):
    params = (
        ('sma_corto', 10), 
        ('sma_largo', 30),
        ('data', None),
        ('operaciones', None),
    )

    def __init__(self):
        self.data1 = self.params.data # asignamos el activo con el que debe operar la instancia de la estrategia
        self.sma_corto = bt.indicators.SimpleMovingAverage(self.data1.close, period=self.params.sma_corto)
        self.sma_largo = bt.indicators.SimpleMovingAverage(self.data1.close, period=self.params.sma_largo)
        self.size = 0
        self.position_active = False # se utiliza para no sobre comprar múltiples veces el mismo activo
        self.order = None
    def next(self):
        if self.order:
            return
        
        # la activación se produce si se detecta un cruce, donde el SMA corto pasa de estar por debajo del largo a estar por encima
        if self.sma_corto[0] > self.sma_largo[0] and self.sma_corto[-1] < self.sma_largo[-1] and not self.position_active:
            # verificamos que el dinero disponible sea suficiente para comprar
            self.size = int(self.broker.getvalue() * 0.10 / self.data1.close[0])
            if self.broker.get_cash() > self.size * self.data1.close[0]:
                self.order = self.buy(data=self.data1, size=self.size)
            else:
                print('El dinero en la cuenta no es suficiente como para efectuar la compra')
        # si el SMA corto pasa de estar por encima del largo a estar por debajo, se vende
        elif self.sma_largo[0] > self.sma_corto[0] and self.sma_largo[-1] < self.sma_corto[-1] and self.position_active:
            self.order = self.sell(data=self.data1, size=self.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.position_active = True
                self.log('compra', self.data1._name, order.executed.price)
            elif order.issell():
                self.position_active = False
                self.log('venta', self.data1._name, order.executed.price)
            self.order = None

    # registramos la operación en la lista
    def log(self, tipo, simbolo, Valor):
        saldo_total = self.broker.getvalue()
        dt = self.data1.datetime.date(0).isoformat()
        self.params.operaciones.append([dt, tipo, 'Cruce de SMA', simbolo, Valor, self.size, (self.size * Valor), self.broker.get_cash(), saldo_total])

cerebro = bt.Cerebro()

cerebro.broker.set_cash(100000)
operaciones = [] #utilizado para almacenar las operaciones realizadas por el bot

data_symbols = ['TSLA', 'MSFT', 'GOOG', 'AAPL']
for symbol in data_symbols:
    df = yf.download(symbol, start='2021-01-01', end='2021-12-31')
    data = bt.feeds.PandasData(dataname=df, name=symbol)
    cerebro.adddata(data)

    # cargamos las estrategias a cada uno de los activos
    cerebro.addstrategy(SMA, velas=10, data=data, operaciones=operaciones)
    cerebro.addstrategy(SMA, velas=30, data=data, operaciones=operaciones)
    cerebro.addstrategy(CruceSMA, sma_corto=10, sma_largo=30, data=data, operaciones=operaciones)

cerebro.run()
print('Valor final de la cartera: %.2f' % cerebro.broker.getvalue())


#guardamos las operaciones en un excel
df_operaciones = pd.DataFrame(operaciones, columns=['Fecha', 'Tipo de operación', 'Estrategia', 'Símbolo', 'Valor','Tamaño de la orden', 'total de la compra','Saldo Disponible Despues de la Operacion',  'Total De la Cuenta'])
df_operaciones.to_excel('resultados_backtesting.xlsx', index=False)

# generamos un grafico con el avance del saldo total para ilustrar mejor el desempeño del bot
plt.figure(figsize=(10, 6))
plt.plot(df_operaciones['Fecha'], df_operaciones['Total De la Cuenta'], label='Saldo Total')
plt.xlabel('Fecha')
plt.ylabel('Saldo Total')
plt.title('Evolución del dinero de la cuenta')
plt.legend()
plt.grid(True)
plt.savefig('resultado.png')

