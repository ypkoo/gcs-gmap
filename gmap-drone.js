var map;
var startLatLng = {lat: 36.374092, lng: 127.365638}
var startLatLng2 = {lat: 36.374383, lng: 127.365327}
var marker;
var droneList = [];
var lineList = [];

var lineSymbol = {
	path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
};

var contentString = 'test string';
var infoWindow = new google.maps.InfoWindow({
    content: contentString
});

function struct_drone() {
	var marker = '';
	var id = '';
}

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: startLatLng,
		zoom: 19,
		mapTypeId: google.maps.MapTypeId.HYBRID
	});

	// var image = 'images/drone.png';

	map.addListener('click', map_clicked);

	//test marker
	var marker = new google.maps.Marker({
		position: startLatLng,
		map: map
	});
}

function map_clicked(event) {
	return;
}

function change_pos(id, lat, lng) {
	var idx = droneList.length;

	// existing drone
	for(var i=0; i<idx; i++) {
		if (id == droneList[i].id) {
			droneList[i].marker.setPosition({lat: lat, lng: lng});
			return;
		}
	}

	// new drone
	var marker = new google.maps.Marker({
		position: {lat: lat, lng: lng},
		map: map
	});

	var infoWindow = new google.maps.InfoWindow({
	    content: ""
	});

	marker.addListener('click', function() {
		infoString = info_string(id);
		infoWindow.setContent(infoString);
		infoWindow.open(map, marker);
	});

	droneList[idx] = new struct_drone();
	droneList[idx].marker = marker;
	droneList[idx].id = id;
}

function info_string(id) {
	for(var i=0; i<idx; i++) {
		if (id == droneList[i].id) {
			drone = droneList[i];
			break;
		}
	}

	if (drone == undefined) {
		return null;
	}
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

function remove_all_markers() {
	for (var i=0; i<droneList; i++) {
		droneList[i].marker.setMap(null);
	}

	markerList = [];
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
	for (var i=0; i<lineList.length; i++) {
		lineList[i].setMap(null);
	}

	lineList = [];
}