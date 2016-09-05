var map;
var startLatLng = {lat: 36.374092, lng: 127.365638}
var startLatLng2 = {lat: 36.374383, lng: 127.365327}
var marker;
var markerList = new Array(10)

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: startLatLng,
		zoom: 19,
		mapTypeId: google.maps.MapTypeId.HYBRID
	});

	var image = 'images/drone.png';
	var text = "this is a sample text."
	var infowindow = new google.maps.InfoWindow({
		content: text
	});
	// marker = new google.maps.Marker({
	// 	position: startLatLng,
	// 	map: map,
	// 	title: 'Hello World!',
	// 	label: '1',
	// 	// icon: image
	// });
	// marker.addListener('click', function() {
	// 	infowindow.open(map, marker);
	// });
}

function change_pos(id, lat, lng) {
	// existing drone
	for(var i=0; i<markerList.length; i++) {
		if (markerList[i] != null && id == markerList[i].id) {
			markerList[i].marker.setPosition({lat: lat, lng: lng});
			return;
		}
	}

	// new drone
	var marker = new google.maps.Makrer({
		position: {lat: lat, lng: lng},
		map: map
	});

	alert('new drone!');

	markerList.push({id: id, marker: marker});
}

function remove_marker(id) {
	for(var i=0; i<markerList.length; i++) {
		if (id == markerList[i].id) {
			markerList[i] = null;
			break;
		}
	}
}