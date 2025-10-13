import { Card, InputNumber, Button, Form } from 'antd';

export default function QuickSettings() {
  return (
    <Card title="Cài đặt nhanh">
      <Form layout="inline">
        <Form.Item label="Số nến giữ tối đa">
          <InputNumber min={1} max={50} defaultValue={12} />
        </Form.Item>
        <Form.Item label="Trailing stop">
          <InputNumber min={0.001} max={0.1} step={0.001} defaultValue={0.002} />
        </Form.Item>
        <Form.Item>
          <Button type="primary">Lưu thay đổi</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}