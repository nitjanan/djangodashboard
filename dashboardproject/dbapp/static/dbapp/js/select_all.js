// เพิ่ม checkbox "เลือกทั้งหมด" ให้กลุ่ม CheckboxSelectMultiple ในหน้า admin
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('ul[id^="id_"]').forEach(function (list) {
        var boxes = list.querySelectorAll('input[type="checkbox"]');
        if (!boxes.length) return;

        var label = document.createElement('label');
        label.style.cssText = 'display:block;margin-bottom:6px;font-weight:bold;';
        var all = document.createElement('input');
        all.type = 'checkbox';
        label.appendChild(all);
        label.appendChild(document.createTextNode(' เลือกทั้งหมด'));
        list.parentNode.insertBefore(label, list);

        function sync() {
            all.checked = Array.prototype.every.call(boxes, function (b) { return b.checked; });
        }
        all.addEventListener('change', function () {
            boxes.forEach(function (b) { b.checked = all.checked; });
        });
        boxes.forEach(function (b) { b.addEventListener('change', sync); });
        sync();
    });
});
