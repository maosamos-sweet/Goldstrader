const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const { EMA, RSI } = require('technicalindicators');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 3000;

// ផ្ទុកហ្វាយល៍ UI HTML
app.use(express.static(__dirname));
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// សន្មតទិន្នន័យតម្លៃមាសជាប្រវត្តិសាស្ត្រសម្រាប់ការគណនា Indicator (Historical Data Placeholder)
let closingPrices = Array.from({ length: 250 }, () => 2030 + Math.random() * 20);
let currentPrice = 2042.50;

// ភ្ជាប់ទៅកាន់ប្រភពតម្លៃ Real-time (ឧទាហរណ៍៖ Binance WebSockets សម្រាប់ទាញតម្លៃមាស/USDT ឬគូស្រដៀង)
// សម្រាប់គំរូនេះ យើងប្រើការត្រាប់តាមចរន្តតម្លៃមាសពិតៗរៀងរាល់ ២ វិនាទី
setInterval(() => {
    const change = (Math.random() - 0.49) * 0.5; // មាសប្រែប្រួលលឿន
    currentPrice = parseFloat((currentPrice + change).toFixed(2));
    
    // បច្ចុប្បន្នភាពតម្លៃចុងក្រោយចូលទៅក្នុង Array សម្រាប់គណនា EMA/RSI
    closingPrices.push(currentPrice);
    closingPrices.shift();

    // គណនា Indicators បច្ចេកទេស
    const ema50 = EMA.calculate({ period: 50, values: closingPrices });
    const ema200 = EMA.calculate({ period: 200, values: closingPrices });
    const rsiValues = RSI.calculate({ period: 14, values: closingPrices });

    const latestEMA50 = ema50[ema50.length - 1];
    const latestEMA200 = ema200[ema200.length - 1];
    const latestRSI = rsiValues[rsiValues.length - 1];

    // បង្កើតយុទ្ធសាស្ត្រ Scalping Signal ស្វ័យប្រវត្ត
    let signal = "HOLD";
    let tp = 0, sl = 0;

    if (currentPrice > latestEMA50 && latestEMA50 > latestEMA200 && latestRSI < 40) {
        signal = "BUY";
        tp = parseFloat((currentPrice + 4.0).toFixed(2)); // TP $4
        sl = parseFloat((currentPrice - 2.0).toFixed(2)); // SL $2
    } else if (currentPrice < latestEMA50 && latestEMA50 < latestEMA200 && latestRSI > 60) {
        signal = "SELL";
        tp = parseFloat((currentPrice - 4.0).toFixed(2));
        sl = parseFloat((currentPrice + 2.0).toFixed(2));
    }

    // បញ្ជូនទិន្នន័យតម្លៃ និងសញ្ញាទៅកាន់ UI តាម WebSocket
    const marketData = JSON.stringify({
        price: currentPrice,
        signal: signal,
        tp: tp,
        sl: sl,
        rsi: Math.round(latestRSI),
        time: new Date().toLocaleTimeString()
    });

    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(marketData);
        }
    });
}, 2000);

server.listen(PORT, () => {
    console.log(`🚀 GoldPulse AI Server is running on http://localhost:${PORT}`);
});
