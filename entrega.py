import backtrader as bt
import yfinance as yf
import csv
import os
class SMA(bt.Strategy):
    params = (
        ('velas', 10), # default en 10, pero se ajusta en la definición de la estrategia
        ('data', None), # recuperamos la data para saber con que activo debe operar esta estrategia
    )

    def __init__(self):
        self.data1 = self.params.data # asignamos el activo con el q debe operar la instancia de la estrategia
        self.sma = bt.indicators.SimpleMovingAverage(self.data1, period=self.params.velas)
        self.size = 0
        self.position_active = False # se utiliza para no sobre comprar multiples veces el mismo activo

    def next(self):
        if self.data1.close[0] > self.sma[0] and not self.position_active:
            #obtenemos el equivalente en acciones que se pueden comprar con el 10% del total de la cartera
            self.size = int((self.broker.getvalue() * 0.10) / self.data1.close[0])
            #verificamos que el dinero disponible sea suficiente para comprar
            if(self.broker.get_cash() > self.size * self.data1.close[0]):
                self.buy(data=self.data1, size=self.size)
                self.position_active = True 
                self.log('compra', self.data1._name, self.data1.close[0])
            else:
                print('el dinero en la cuenta no es suficiente como para efectuar la compra')
        elif self.data1.close[0] < self.sma[0] and self.position_active:
            self.sell(data=self.data1, size=self.size)
            self.position_active = False # se libera la posición para poder comprar nuevamente
            self.log('venta', self.data1._name, self.data1.close[0])

    #registramos la operacion en el archivo csv
    def log(self, tipo, simbolo, monto):
        saldo_total = self.broker.getvalue()
        dt = self.data1.datetime.date(0).isoformat()
        with open('operaciones.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([dt, tipo, f'SMA {self.params.velas}', simbolo, monto, saldo_total])

class CruceSMA(bt.Strategy):
    params = (
        ('sma_corto', 10), 
        ('sma_largo', 30),
        ('data', None),
    )

    def __init__(self):
        self.data1 = self.params.data # asignamos el activo con el q debe operar la instancia de la estrategia
        self.sma_corto = bt.indicators.SimpleMovingAverage(self.data1.close, period=self.params.sma_corto)
        self.sma_largo = bt.indicators.SimpleMovingAverage(self.data1.close, period=self.params.sma_largo)
        self.size = 0
        self.position_active = False # se utiliza para no sobre comprar multiples veces el mismo activo
        
    def next(self):
        # la activacion se produce si de detecta un cruce, donde el sma corto pasa de estar por debajo del largo a estar por encima
        if self.sma_corto[0] > self.sma_largo[0] and self.sma_corto[-1] < self.sma_largo[-1] and not self.position_active:
            #verificamos que el dinero disponible sea suficiente para comprar
            self.size = int(self.broker.getvalue() * 0.10 / self.data1.close[0])
            if(self.broker.get_cash() > self.size * self.data1.close[0]):
                self.buy(data=self.data1, size=self.size)
                self.position_active = True
                self.log('compra', self.data1._name, self.data1.close[0])
            else:
                print('el dinero en la cuenta no es suficiente como para efectuar la compra')
        # si el sma corto pasa de estar por encima del largo a estar por debajo, se vende
        elif self.sma_largo[0] > self.sma_corto[0] and self.sma_largo[-1] < self.sma_corto[-1] and self.position_active:
            self.sell(data=self.data1, size=self.size)
            self.position_active = False # se libera la posición para poder comprar nuevamente
            self.log('venta', self.data1._name, self.data1.close[0])

    #registramos la operacion en el archivo csv
    def log(self, tipo, simbolo, monto):
        saldo_total = self.broker.getvalue()
        dt = self.data1.datetime.date(0).isoformat()
        with open('operaciones.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([dt, tipo, 'Cruce de SMA', simbolo, monto, saldo_total])

cerebro = bt.Cerebro()

cerebro.broker.set_cash(100000)

data_symbols = ['TSLA', 'MSFT', 'GOOG', 'AAPL']
for symbol in data_symbols:
    df = yf.download(symbol, start='2021-01-01', end='2021-12-31')
    data = bt.feeds.PandasData(dataname=df, name=symbol)
    cerebro.adddata(data)

    # cargamos las estrategias a cada uno de los activos
    cerebro.addstrategy(SMA, velas=10, data=data)
    cerebro.addstrategy(SMA, velas=30, data=data)
    cerebro.addstrategy(CruceSMA, sma_corto=10, sma_largo=30, data=data)

#reiniciamos el txt
if os.path.exists('operaciones.csv'):
    os.remove('operaciones.csv')
cerebro.run()
print('Valor final de la cartera: %.2f' % cerebro.broker.getvalue())
