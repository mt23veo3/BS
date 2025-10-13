import { Card, Row, Col, Statistic, Table, Alert } from 'antd';
import CandlestickChart from '../components/CandlestickChart';
import QuickStats from '../components/QuickStats';
import NotificationBar from '../components/NotificationBar';

export default function Dashboard() {
  return (
    <div>
      <Row gutter={24}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Lãi/lỗ hôm nay"
              value={123.45}
              precision={2}
              valueStyle={{ color: '#3f8600', fontSize: 28 }}
              suffix="USDT"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Số lệnh đang mở" value={2} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Tỷ lệ lệnh thắng" value={67} suffix="%" />
          </Card>
        </Col>
      </Row>
      <Row gutter={24} style={{ marginTop: 24 }}>
        <Col span={16}>
          <Card title="Biểu đồ giá (Demo)">
            <CandlestickChart />
          </Card>
        </Col>
        <Col span={8}>
          <NotificationBar />
        </Col>
      </Row>
    </div>
  );
}