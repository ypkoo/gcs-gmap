var map;
var startLatLng = {lat: 36.374092, lng: 127.365638}
var startLatLng2 = {lat: 36.374383, lng: 127.365327}
var marker;
var droneList = []
var lineList = []

var lineSymbol = {
	path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
};

var contentString = 'test string';
var infoWindow = new google.maps.InfoWindow({
	content: null
});

function struct_drone(marker, id) {
	var marker = marker;
	var id = id;
}


function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: startLatLng,
		zoom: 19,
		mapTypeId: google.maps.MapTypeId.HYBRID
	});

	var image = 'images/drone.png';
}

function change_pos(id, lat, lng) {
	var idx = droneList.length;

	// existing drone
	for(var i=0; i<idx; i++) {
		if (droneList[i] != null && id == droneList[i].id) {
			droneList[i].marker.setPosition({lat: lat, lng: lng});
			return;
		}
	}

	// new drone
	var marker = new google.maps.Marker({
		position: {lat: lat, lng: lng},
		map: map
	});

	marker.addListener('click', function() {
		infoWindow.setContent(contentString);
		infoWindow.open(map, marker);
	});

	var new_drone = new struct_drone(marker, id);
	droneList.push(new_drone);
}

function remove_marker(id) {
	for(var i=0; i<droneList.length; i++) {
		if (id == droneList[i].id) {
			droneList.marker.setMap(null);
			droneList[i] = null;
			break;
		}
	}
}

function draw_line(startLat, startLng, endLat, endLng) {
	var line = new google.maps.Polyline({
	path: [{lat: startLat, lng: startLng}, {lat: endLat, lng: endLng}],
	icons: [{
		icon: lineSymbol,
		offset: '100%'
	}],
	map: map
	});

	lineList.push(line);
}

function remove_all_lines() {
	for (var i=0; i<line.length; i++) {
		lineList[i].setMap(null);
	}

	lineList = [];
}