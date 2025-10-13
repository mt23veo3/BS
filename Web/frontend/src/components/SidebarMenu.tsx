import { Menu } from 'antd';
import {
  HomeOutlined,
  FundOutlined,
  BarChartOutlined,
  LineChartOutlined,
  NotificationOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons';

interface Props {
  onSelect: (key: string) => void;
}

export default function SidebarMenu({ onSelect }: Props) {
  return (
    <Menu
      theme="dark"
      mode="inline"
      defaultSelectedKeys={['dashboard']}
      onClick={({ key }) => onSelect(key)}
      items={[
        { key: 'dashboard', icon: <HomeOutlined />, label: 'Trang chủ' },
        { key: 'pnl', icon: <FundOutlined />, label: 'Báo cáo PnL' },
        { key: 'orders', icon: <BarChartOutlined />, label: 'Báo cáo Lệnh' },
        { key: 'signals', icon: <LineChartOutlined />, label: 'Báo cáo Tín hiệu' },
        { key: 'alerts', icon: <NotificationOutlined />, label: 'Cảnh báo' },
        { key: 'settings', icon: <SettingOutlined />, label: 'Cài đặt nhanh' },
        { key: 'account', icon: <UserOutlined />, label: 'Tài khoản' },
      ]}
    />
  );
}