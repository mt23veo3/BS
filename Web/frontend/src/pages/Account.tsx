import { Card } from 'antd';

export default function Account() {
  return (
    <Card title="Tài khoản">
      <p>Tên đăng nhập: admin</p>
      <p><a href="#">Đổi mật khẩu</a></p>
      <p><a href="#">Đăng xuất</a></p>
    </Card>
  );
}